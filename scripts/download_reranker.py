"""Download the pinned ONNX reranker; no inference, conversion or remote code."""
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
    parser.add_argument('--manifest', default=str(Path(__file__).resolve().parents[1]/'src/research_rag_mcp/reranker_manifest.json'))
    args = parser.parse_args()
    manifest = json.loads(Path(args.manifest).read_text())
    if manifest['model_id'] != 'onnx-community/bge-reranker-v2-m3-ONNX':
        raise ValueError('Unexpected reranker model')
    print('Reranker:', manifest['model_id'], manifest['revision'], 'CPU only', flush=True)
    for name, expected in manifest['files'].items():
        target = Path(args.destination)/name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_file() and digest(target) == expected:
            print('Verified:', name, flush=True)
            continue
        partial = target.with_suffix(target.suffix+'.part')
        url = f'https://huggingface.co/{manifest["model_id"]}/resolve/{manifest["revision"]}/{name}'
        try:
            with urllib.request.urlopen(url, timeout=120) as response, partial.open('wb') as output:
                while block := response.read(1024*1024):
                    output.write(block)
            if digest(partial) != expected:
                raise ValueError('Reranker hash mismatch: '+name)
            partial.replace(target)
        finally:
            partial.unlink(missing_ok=True)
        print('Downloaded and verified:', name, flush=True)


if __name__ == '__main__':
    main()
