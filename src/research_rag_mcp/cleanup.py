"""Explicit cleanup, including an inbox-preserving permanent data purge."""
import hashlib
import json
import secrets

from .purge import PermanentPurge, inventory


SCOPES = ('search_index', 'documents', 'workspace', 'all_except_inbox')
TABLES = ('embeddings', 'chunk_metadata', 'chunk_sets', 'chunks', 'documents',
          'versions', 'artifacts', 'searches', 'events')
PRESERVED = ['inbox files', 'imported original files in sources/', 'exports',
             'existing backups', 'authentication tokens', 'embedding model files']


class WorkspaceCleanup(PermanentPurge):
    def _cleanup_plan(self, db, state, scope):
        if scope not in SCOPES:
            raise ValueError('scope must be search_index, documents, workspace or all_except_inbox')
        tables = TABLES[:1] if scope == 'search_index' else TABLES[:5] if scope == 'documents' else TABLES
        counts = {table: db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
                  if table in tables else 0 for table in TABLES}
        artifact_count = db.execute('SELECT count(*) FROM artifacts').fetchone()[0]
        version_count = db.execute('SELECT count(*) FROM versions').fetchone()[0]
        blockers = []
        if scope == 'documents' and (artifact_count or version_count):
            blockers.append('Document-only cleanup is blocked while artifacts or historical versions exist. '
                            'Keep the evidence, or explicitly choose workspace cleanup to archive and clear them together.')
        receipts = [json.loads(row['response']) for row in db.execute('SELECT response FROM requests WHERE response IS NOT NULL')]
        retired = sum(r.get('result', {}).get('operation') != 'cleanup_workspace' for r in receipts)
        plan = {'scope': scope, 'revision': state['revision'], 'workspace': str(self.root),
                'delete_counts': counts, 'clears_project': scope in ('workspace', 'all_except_inbox'),
                'retires_mutation_receipts': retired,
                'source_ids': sorted(state['sources']),
                'artifact_ids': sorted(state['artifacts']),
                'source_files_retained': len(state['sources']), 'preserves': PRESERVED,
                'backup_required': True, 'can_execute': not blockers, 'blockers': blockers,
                'limitation': 'Clears database records only. Original files are retained; this is not secure erasure. '
                              'Index cleanup requires rebuild_search_index before semantic/hybrid retrieval. '
                              'Cleanup by itself does not improve semantic relevance.'}
        if scope == 'all_except_inbox':
            files, inbox = inventory(self.root)
            plan.update(backup_required=False, source_files_retained=0,
                preserves=['all inbox files', 'server authentication token', 'database schema and cleanup receipt'],
                filesystem=files, inbox=inbox, retires_mutation_receipts=0,
                limitation='Permanently deletes all workspace research records and data files outside inbox, '
                           'including source copies, exports, backups and import-runs. No new backup. '
                           'Server code/configuration and external model assets are outside this data workspace. '
                           'Not forensic secure erasure. A partial filesystem failure remains resumable and blocks new writes.')
            plan['delete_counts']['requests'] = db.execute('SELECT count(*) FROM requests').fetchone()[0]
        encoded = json.dumps(plan, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()
        return {**plan, 'plan_hash': hashlib.sha256(encoded).hexdigest()}

    def preview_workspace_cleanup(self, scope):
        with self.connect() as db:
            db.execute('BEGIN')
            self.require_no_pending_cleanup(db)
            return self._cleanup_plan(db, self.state(db), scope)

    def cleanup_workspace(self, scope, plan_hash, expected_revision, key):
        if scope not in SCOPES or not isinstance(plan_hash, str) or len(plan_hash) != 64:
            raise ValueError('Supply a supported scope and the plan_hash from preview_workspace_cleanup')
        if scope == 'all_except_inbox':
            return self.purge_workspace(plan_hash, expected_revision, key)

        def action(db, state):
            plan = self._cleanup_plan(db, state, scope)
            if not secrets.compare_digest(plan_hash, plan['plan_hash']):
                raise ValueError('Cleanup plan changed; call preview_workspace_cleanup again')
            if plan['blockers']:
                raise ValueError('; '.join(plan['blockers']))
            # mutate holds BEGIN IMMEDIATE, so the separate read connection used by
            # backup sees this exact committed revision. No live record changes until
            # the SQLite/source snapshot and its hash manifest have been completed.
            backup = self.backup()
            tables = TABLES[:1] if scope == 'search_index' else TABLES[:5] if scope == 'documents' else TABLES
            for table in tables:
                db.execute(f'DELETE FROM {table}')
            if scope == 'workspace':
                db.execute('UPDATE meta SET project=NULL WHERE id=1')
            # Retain keys as tombstones: retries of old imports/rebuilds must not
            # falsely report success against data which cleanup has just removed.
            # Keep cleanup receipts themselves so exact cleanup retries stay inert.
            for row in db.execute('SELECT key,response FROM requests WHERE response IS NOT NULL').fetchall():
                receipt = json.loads(row['response'])
                if receipt.get('result', {}).get('operation') != 'cleanup_workspace':
                    db.execute('UPDATE requests SET response=NULL WHERE key=?', (row['key'],))
            return {'operation': 'cleanup_workspace', 'scope': scope, 'deleted': plan['delete_counts'],
                    'cleared_project': plan['clears_project'], 'backup': backup,
                    'source_files_retained': plan['source_files_retained'], 'preserves': PRESERVED,
                    'retired_mutation_receipts': plan['retires_mutation_receipts'],
                    'next_step': 'rebuild_search_index' if scope == 'search_index' else 'import_document',
                    'quality_improvement_claimed': False}

        return self.mutate('cleanup_workspace', {'scope': scope, 'plan_hash': plan_hash},
                           expected_revision, key, action)
