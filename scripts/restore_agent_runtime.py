#!/usr/bin/env python3
"""Restore a minimal pinned runtime from exact connector file contents, offline.

This transports source, not ownership or Oracle data. It does not bypass host
network policy. The agent must obtain the manifest and files from one trusted
commit through an authorized connector and preserve exact UTF-8 content.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile

FILES = frozenset((
    'ai_deckbuilding_tool/__init__.py', 'ai_deckbuilding_tool/__main__.py',
    'ai_deckbuilding_tool/collection_import.py', 'tools/agent_gateway.py',
    'tools/agent_workflow.py', 'tools/card_search.py', 'tools/card_identity.py',
    'tools/atomic_runtime.py', 'validator/MTG_Deck_Validator_v1.1.1.py',
    'AGENTS.md', 'START_HERE.md', 'README.md', 'PROJECT_STATUS.md',
    'docs/AGENT_QUICKSTART.md', 'docs/AGENT_WORKFLOW_MVP.md',
    'docs/AGENT_SOURCE_COMPATIBILITY_P4.md', 'docs/AGENT_SOURCE_BOOTSTRAP.md',
    'prompts/casual/builder/stable/MTG_Deck_Builder_v7.4_full.md',
    'prompts/casual/tester/MTG_Deck_Tester_v3.4.2_full.md',
    'scripts/restore_agent_runtime.py',
))
MAX_FILE = 4 * 1024 * 1024
MAX_PAYLOAD = 8 * 1024 * 1024


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def parse(raw):
    def reject(value):
        raise ValueError('INVALID_JSON_CONSTANT')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=reject)


def safe(path):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('UNSAFE_SYMLINK_PATH')
    return path


def read(path, limit):
    path = safe(path)
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise ValueError('INPUT_NOT_REGULAR_OR_TOO_LARGE')
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('INPUT_TOO_LARGE')
    return raw


def restore(manifest_raw, payload, destination, expected_commit, expected_manifest_sha256):
    if not re.fullmatch('[a-f0-9]{40}', expected_commit):
        raise ValueError('INVALID_COMMIT')
    if (len(manifest_raw) > 65536 or not re.fullmatch('[a-f0-9]{64}', expected_manifest_sha256)
            or hashlib.sha256(manifest_raw).hexdigest() != expected_manifest_sha256):
        raise ValueError('MANIFEST_HASH_MISMATCH')
    manifest = parse(manifest_raw)
    if not isinstance(manifest, dict) or set(manifest) != {'schema_version', 'files'} or manifest['schema_version'] != 1:
        raise ValueError('INVALID_SOURCE_MANIFEST')
    if not isinstance(payload, dict) or set(payload) != {'commit', 'files'} or payload['commit'] != expected_commit:
        raise ValueError('COMMIT_MISMATCH')
    entries, sources = manifest['files'], payload['files']
    if (not isinstance(entries, dict) or not isinstance(sources, dict)
            or set(entries) != FILES or set(sources) != FILES):
        raise ValueError('UNEXPECTED_SOURCE_FILE_SET')
    verified = {}
    total = 0
    for name in sorted(FILES):
        if not isinstance(entries[name], str) or not re.fullmatch('[a-f0-9]{64}', entries[name]):
            raise ValueError('INVALID_SOURCE_HASH')
        if not isinstance(sources[name], str):
            raise ValueError('INVALID_SOURCE_CONTENT')
        raw = sources[name].encode('utf-8')
        total += len(raw)
        if len(raw) > MAX_FILE or total > MAX_PAYLOAD:
            raise ValueError('SOURCE_TOO_LARGE')
        if hashlib.sha256(raw).hexdigest() != entries[name]:
            raise ValueError('SOURCE_HASH_MISMATCH')
        verified[name] = raw
    dest = safe(destination)
    if dest.exists():
        raise ValueError('DESTINATION_ALREADY_EXISTS')
    if not dest.parent.is_dir():
        raise ValueError('DESTINATION_PARENT_UNAVAILABLE')
    stage = Path(tempfile.mkdtemp(prefix='.agent-runtime-', dir=dest.parent))
    try:
        for name, raw in verified.items():
            path = stage / name
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with path.open('xb') as stream:
                stream.write(raw)
            path.chmod(0o600)
        receipt = dict(schema_version=1, source_commit=expected_commit,
                       manifest_sha256=expected_manifest_sha256, files=entries,
                       transport='AUTHORIZED_CONNECTOR_CONTENT', git_checkout=False,
                       oracle_included=False, collection_included=False)
        (stage / 'SOURCE_RECEIPT.json').write_text(json.dumps(receipt, indent=2)+'\n')
        (stage / 'SOURCE_RECEIPT.json').chmod(0o600)
        os.rename(stage, dest)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return dict(status='SOURCE_RUNTIME_RESTORED', source_commit=expected_commit,
                manifest_sha256=expected_manifest_sha256, file_count=len(FILES),
                validated=False, oracle_setup='NOT_EXECUTED',
                next_action='RUN_PYTHON_MODULE_SETUP_FROM_DESTINATION',
                limitations=['Source commit labels are caller declarations; obtain files from a trusted pinned connector response.',
                             'Local checksums are integrity records, not independent signatures.',
                             'Official MTGJSON access or an intact verified cache is still required.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--payload', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--expected-commit', required=True)
    parser.add_argument('--expected-manifest-sha256', required=True)
    args = parser.parse_args()
    try:
        report = restore(read(args.manifest, 65536), parse(read(args.payload, MAX_PAYLOAD)),
                         args.destination, args.expected_commit, args.expected_manifest_sha256)
        code = 0
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError) as exc:
        reason = str(exc) if isinstance(exc, ValueError) and re.fullmatch('[A-Z_]+', str(exc)) else 'SOURCE_RESTORE_FAILED'
        report = dict(status='SOURCE_RESTORE_BLOCKED', reason=reason, validated=False)
        code = 3
    print(json.dumps(report, sort_keys=True))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
