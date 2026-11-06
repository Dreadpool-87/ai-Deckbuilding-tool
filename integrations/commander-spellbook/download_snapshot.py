#!/usr/bin/env python3
"""Explicit local fetch of official Commander Spellbook bulk snapshot; no automatic Actions."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from urllib.request import Request, urlopen

URL = 'https://json.commanderspellbook.com/variants.json.gz'
MAX_BYTES = 256 * 1024 * 1024


def download(destination: Path) -> dict:
    if destination.exists():
        raise FileExistsError(f'Refusing to overwrite {destination}; choose a new path')
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='.spellbook-',
                                         suffix='.part', delete=False) as f:
            temporary = Path(f.name)
            request = Request(URL, headers={'User-Agent': 'MTG-Deck-Tools-Spellbook-Offline-Analyzer/0.1'})
            with urlopen(request, timeout=60) as response:
                total = 0
                digest = hashlib.sha256()
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    total += len(block)
                    if total > MAX_BYTES:
                        raise ValueError('Downloaded archive exceeds 256 MiB safety limit')
                    f.write(block)
                    digest.update(block)
        with temporary.open('rb') as f:
            if f.read(2) != b'\x1f\x8b':
                raise ValueError('Downloaded content is not a gzip archive')
        os.replace(temporary, destination)
        temporary = None
        return {'source': URL, 'file': str(destination), 'size_bytes': total,
                'sha256': digest.hexdigest(), 'status': 'DOWNLOADED_UNVALIDATED_SCHEMA'}
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(download(args.output), indent=2))
