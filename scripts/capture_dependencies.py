"""Capture installed distribution provenance, source-file hashes and notices."""
import hashlib
import importlib.metadata as metadata
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[1]
out = root / 'third-party'
out.mkdir(exist_ok=True)
records = []
distributions = list(metadata.distributions())
incomplete = [str(d._path.name) for d in distributions if not d.metadata.get('Name')]
for dist in sorted((d for d in distributions if d.metadata.get('Name')), key=lambda d: d.metadata['Name'].lower()):
    name = dist.metadata['Name']
    if name.lower() in {'tts-research', 'codex-research-rag-mcp'}:
        continue
    record = dict(name=name, version=dist.version,
                  upstream=dist.metadata.get_all('Project-URL') or [],
                  license=dist.metadata.get('License-Expression') or dist.metadata.get('License'),
                  notices=[], source_files=[])
    for entry in dist.files or []:
        path = Path(dist.locate_file(entry))
        if not path.is_file() or '..' in entry.parts:
            continue
        notice = any(word in entry.name.lower() for word in ('license', 'notice', 'copying', 'copyright'))
        if entry.suffix == '.py' or (notice and entry.suffix != '.pyc'):
            raw = path.read_bytes()
            item = {'distribution_path': str(entry), 'sha256': hashlib.sha256(raw).hexdigest()}
            if notice and entry.suffix not in ('.py', '.pyc'):
                dest = out / 'licenses' / f'{name}-{dist.version}' / str(entry)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(raw)
                item['local_path'] = str(dest.relative_to(root))
                record['notices'].append(item)
            elif entry.suffix == '.py':
                record['source_files'].append(item)
    records.append(record)
(out / 'dependencies.json').write_text(json.dumps({
    'platform': platform.platform(), 'python': sys.version,
    'captured_at': datetime.now(timezone.utc).isoformat(),
    'method': 'Installed distribution inspection; selected application-source provenance is recorded separately under third-party/reference-rag.',
    'incomplete_metadata_directories': incomplete,
    'packages': records,
}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'Captured {len(records)} installed distributions with file hashes and notices')
