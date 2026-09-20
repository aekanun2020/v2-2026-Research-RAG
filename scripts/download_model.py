"""Fetch only the pinned original model assets, checking hashes before installation."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('destination')
    parser.add_argument('--manifest', default=str(Path(__file__).resolve().parents[1]/'src/research_rag_mcp/model_manifest.json'))
    args = parser.parse_args()
    manifest = json.loads(Path(args.manifest).read_text())
    assert manifest['model_id'] == 'intfloat/multilingual-e5-base'
    print('Embedding model:', manifest['model_id'], 'revision:', manifest['revision'], 'runtime: CPU only', flush=True)
    destination = Path(args.destination)
    for name, expected in manifest['files'].items():
        target = destination/name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and digest(target) == expected:
            print('Verified existing:', name, flush=True)
            continue
        url = f'https://huggingface.co/{manifest["model_id"]}/resolve/{manifest["revision"]}/{name}'
        partial = target.with_suffix(target.suffix+'.part')
        try:
            with urllib.request.urlopen(url, timeout=120) as response, partial.open('wb') as output:
                while block := response.read(1024*1024):
                    output.write(block)
            if digest(partial) != expected:
                raise ValueError('Model asset hash mismatch: '+name)
            partial.replace(target)
        finally:
            partial.unlink(missing_ok=True)
        print('Downloaded and verified:', name, flush=True)


if __name__ == '__main__':
    main()
