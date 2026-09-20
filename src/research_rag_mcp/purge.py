"""Durable permanent cleanup: no backup, no path input, inbox bytes preserved."""
import hashlib
import json
import secrets
import stat


RUNTIME_FILES = {'.http-token', 'research.sqlite', 'research.sqlite-journal',
                 'research.sqlite-wal', 'research.sqlite-shm'}
DATA_DIRECTORIES = {'sources', 'exports', 'backups'}
DATA_TABLES = ('embeddings', 'chunk_metadata', 'chunk_sets', 'chunks', 'documents',
               'versions', 'artifacts', 'searches', 'events', 'requests')


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def digest_file(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def tree(path, base):
    """Inventory regular files/directories without following symbolic links."""
    info = path.lstat()
    name = path.relative_to(base).as_posix()
    if stat.S_ISLNK(info.st_mode):
        raise ValueError('Cleanup refuses symbolic link: '+name)
    if stat.S_ISREG(info.st_mode):
        return [dict(path=name, kind='file', bytes=info.st_size, sha256=digest_file(path))]
    if not stat.S_ISDIR(info.st_mode) or path.is_mount():
        raise ValueError('Cleanup refuses special file or nested mount: '+name)
    records = [dict(path=name, kind='directory')]
    for child in sorted(path.iterdir()):
        records.extend(tree(child, base))
    return records


def summarize(entries):
    return {'entries': entries, 'files': sum(e['kind'] == 'file' for e in entries),
            'bytes': sum(e.get('bytes', 0) for e in entries),
            'sha256': hashlib.sha256(encode(entries).encode()).hexdigest()}


def inventory(root):
    inbox = root/'inbox'
    if inbox.is_symlink() or not inbox.is_dir():
        raise ValueError('Inbox must be a real directory; cleanup refuses symbolic links')
    entries = []
    for path in sorted(root.iterdir()):
        if path.name == 'inbox':
            continue
        if path.name in RUNTIME_FILES:
            if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
                raise ValueError('Unsafe runtime file; cleanup refused: '+path.name)
            continue
        entries.extend(tree(path, root))
    inbox_entries = []
    for path in sorted(inbox.iterdir()):
        inbox_entries.extend(tree(path, inbox))
    protected = summarize(inbox_entries)
    # File hashes bind the preview; only the aggregate is needed in the receipt.
    protected.pop('entries')
    return summarize(entries), protected


class PermanentPurge:
    @staticmethod
    def require_no_pending_cleanup(db):
        if db.execute('SELECT 1 FROM cleanup_jobs WHERE id=1').fetchone():
            raise ValueError('Pending cleanup must be resumed with its original scope, plan_hash, revision and idempotency_key before new writes')

    def purge_workspace(self, plan_hash, expected_revision, key):
        if not isinstance(key, str) or not key.strip() or len(key) > 200:
            raise ValueError('idempotency_key requires nonempty text of at most 200 characters')
        payload = {'scope': 'all_except_inbox', 'plan_hash': plan_hash}
        fingerprint = hashlib.sha256(encode(['cleanup_workspace', payload, 'mcp-client']).encode()).hexdigest()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT * FROM requests WHERE key=?', (key,)).fetchone()
            if previous:
                if previous['response'] is None:
                    raise ValueError('Idempotency key retired by cleanup; use a new key')
                if previous['fingerprint'] != fingerprint:
                    raise ValueError('Idempotency key already used with different input')
                return json.loads(previous['response'])
            pending = db.execute('SELECT data FROM cleanup_jobs WHERE id=1').fetchone()
            if pending:
                job = json.loads(pending['data'])
                if (job['idempotency_key'] != key or job['plan_hash'] != plan_hash
                        or job['expected_revision'] != expected_revision):
                    raise ValueError('Pending cleanup requires the exact original arguments')
            else:
                state = self.state(db)
                if expected_revision != state['revision']:
                    raise ValueError('Stale revision; read workspace_status and reconsider')
                plan = self._cleanup_plan(db, state, 'all_except_inbox')
                if not secrets.compare_digest(plan_hash, plan['plan_hash']):
                    raise ValueError('Cleanup plan changed; call preview_workspace_cleanup again')
                job = dict(scope='all_except_inbox', plan_hash=plan_hash, expected_revision=expected_revision,
                           idempotency_key=key, fingerprint=fingerprint, plan=plan,
                           revision=state['revision']+1)
                db.execute('PRAGMA secure_delete=ON')
                for table in DATA_TABLES:
                    db.execute(f'DELETE FROM {table}')
                db.execute('UPDATE meta SET project=NULL,revision=? WHERE id=1', (job['revision'],))
                db.execute('INSERT INTO cleanup_jobs VALUES(1,?)', (encode(job),))
        # The irreversible database change and durable job commit before file
        # removal. Missing planned files on retry mean prior removal succeeded.
        return self._finish_purge(key, plan_hash)

    def _finish_purge(self, key, plan_hash):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            pending = db.execute('SELECT data FROM cleanup_jobs WHERE id=1').fetchone()
            if not pending:
                previous = db.execute('SELECT response FROM requests WHERE key=?', (key,)).fetchone()
                if previous and previous['response']:
                    return json.loads(previous['response'])
                raise ValueError('Cleanup job is missing; inspect workspace status')
            job = json.loads(pending['data'])
            if job['idempotency_key'] != key or job['plan_hash'] != plan_hash:
                raise ValueError('Pending cleanup requires the exact original arguments')
            plan = job['plan']
            result = {'operation': 'cleanup_workspace', 'scope': job['scope'],
                      'deleted': plan['delete_counts'], 'backup': None, 'source_files_retained': 0,
                      'inbox': plan['inbox'], 'preserves': plan['preserves'],
                      'next_step': 'import_document', 'quality_improvement_claimed': False}
            try:
                current, protected = inventory(self.root)
                if protected != plan['inbox']:
                    raise ValueError('Inbox changed since preview; inspect it before resuming cleanup')
                planned = {entry['path']: entry for entry in plan['filesystem']['entries']}
                for entry in current['entries']:
                    if planned.get(entry['path']) != entry:
                        raise ValueError('Workspace file changed during cleanup: '+entry['path'])
                for entry in sorted(current['entries'], key=lambda e: (e['path'].count('/'), e['path']), reverse=True):
                    path = self.root/entry['path']
                    if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != self.root and p.is_relative_to(self.root)):
                        raise ValueError('Cleanup refuses symbolic link: '+entry['path'])
                    if entry['kind'] == 'file':
                        path.unlink()
                    elif entry['path'] not in DATA_DIRECTORIES:
                        path.rmdir()
                remaining, protected = inventory(self.root)
                if protected != plan['inbox']:
                    raise ValueError('Inbox changed during cleanup; verification failed')
                if any(e['path'] not in DATA_DIRECTORIES for e in remaining['entries']):
                    raise ValueError('Unplanned data remains; cleanup is incomplete')
            except (OSError, ValueError) as exc:
                return {'revision': job['revision'], 'result': {**result, 'status': 'incomplete',
                    'inbox_unchanged': None, 'source_files_retained': None,
                    'reason': str(exc), 'database_cleared': True, 'filesystem_complete': False,
                    'resume_with': {k: job[k] for k in ('scope', 'plan_hash', 'expected_revision', 'idempotency_key')}}}
            response = {'revision': job['revision'], 'result': {**result, 'status': 'completed',
                        'database_cleared': True, 'filesystem_complete': True, 'inbox_unchanged': True,
                        'deleted_files': plan['filesystem']['files'], 'deleted_bytes': plan['filesystem']['bytes']}}
            db.execute('PRAGMA secure_delete=ON')
            db.execute('DELETE FROM cleanup_jobs')
            db.execute('INSERT INTO requests VALUES(?,?,?)', (key, job['fingerprint'], encode(response)))
            return response
