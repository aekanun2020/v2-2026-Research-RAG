"""Durable permanent cleanup: no backup, no path input, inbox bytes preserved."""
import hashlib
import json
import secrets
import stat


RUNTIME_FILES = {'workspace.json', '.workspace.lock'}
DATA_DIRECTORIES = {'sources', 'exports', 'backups', 'jobs'}


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
