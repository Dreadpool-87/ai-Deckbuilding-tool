"""Official AtomicCards verification and private local cache; no redistribution.

Receipts establish byte integrity and recorded HTTPS provenance, not signatures
against a hostile process running as the same operating-system user.
"""
from __future__ import annotations

from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import tempfile
from urllib.request import Request, urlopen

BASE = 'https://mtgjson.com/api/v5/'
ARCHIVE = 'AtomicCards.json.gz'
MAX_ARCHIVE = 120 * 1024 * 1024
MAX_JSON = 512 * 1024 * 1024
MAX_RECEIPT = 16384


def safe_path(path):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('UNSAFE_SYMLINK_PATH')
    return path


def read_file(path, limit):
    path = safe_path(path)
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise ValueError('INPUT_NOT_REGULAR_OR_TOO_LARGE')
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('INPUT_TOO_LARGE')
    return raw


def strict_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def strict_json(raw):
    def reject(value):
        raise ValueError('NONFINITE_JSON')
    return json.loads(raw, object_pairs_hook=strict_pairs, parse_constant=reject)


def response(name):
    request = Request(BASE + name, headers={'User-Agent': 'AI-Deckbuilding-Tool/1.0', 'Cache-Control': 'no-cache'})
    result = urlopen(request, timeout=45)
    if result.geturl() != BASE + name:
        result.close()
        raise ValueError('UNEXPECTED_UPSTREAM_REDIRECT')
    return result


def fetch(name, limit=131072):
    with response(name) as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('UPSTREAM_METADATA_TOO_LARGE')
    return raw


def checksum(raw):
    match = re.fullmatch(r'([a-fA-F0-9]{64})(?:\s+\*?AtomicCards\.json\.gz)?', raw.decode('ascii').strip())
    if not match:
        raise ValueError('INVALID_OFFICIAL_CHECKSUM')
    return match[1].lower()


def upstream():
    meta = strict_json(fetch('Meta.json'))
    version = meta.get('data', {}).get('version') if isinstance(meta, dict) else None
    if not isinstance(version, str) or not re.fullmatch(r'[A-Za-z0-9_.+-]{1,100}', version):
        raise ValueError('INVALID_UPSTREAM_VERSION')
    return version, checksum(fetch(ARCHIVE + '.sha256'))


def download(path):
    total = 0
    with response(ARCHIVE) as stream, path.open('xb') as target:
        while block := stream.read(1024 * 1024):
            total += len(block)
            if total > MAX_ARCHIVE:
                raise ValueError('ARCHIVE_TOO_LARGE')
            target.write(block)
        target.flush()
        os.fsync(target.fileno())


def inspect_archive(path, expected, version):
    if not isinstance(expected, str) or not re.fullmatch('[a-f0-9]{64}', expected):
        raise ValueError('INVALID_EXPECTED_SHA256')
    raw = read_file(path, MAX_ARCHIVE)
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('ORACLE_SHA256_MISMATCH')
    # Bounded decompression also checks gzip CRC/trailer. Parse strict JSON.
    import io
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
        unpacked = stream.read(MAX_JSON + 1)
    if len(unpacked) > MAX_JSON:
        raise ValueError('DECOMPRESSED_ORACLE_TOO_LARGE')
    payload = strict_json(unpacked)
    if (not isinstance(payload, dict) or not isinstance(payload.get('meta'), dict)
            or payload['meta'].get('version') != version
            or not isinstance(payload.get('data'), dict) or len(payload['data']) < 20000):
        raise ValueError('INVALID_FULL_ATOMIC_SCHEMA_OR_VERSION')
    records = 0
    for name, faces in payload['data'].items():
        if not isinstance(name, str) or not name.strip() or not isinstance(faces, list) or not faces:
            raise ValueError('INVALID_ATOMIC_CARD_GROUP')
        for card in faces:
            # Multifaced groups legitimately contain differing face names. Identity
            # contradictions remain the responsibility of the existing identity layer.
            if (not isinstance(card, dict) or not isinstance(card.get('name'), str)
                    or not card['name'].strip() or not isinstance(card.get('types'), list)
                    or not card['types'] or not all(isinstance(t, str) for t in card['types'])
                    or type(card.get('manaValue')) not in (int, float)
                    or not math.isfinite(card['manaValue']) or card['manaValue'] < 0):
                raise ValueError('INVALID_ATOMIC_CARD_RECORD')
            records += 1
    return dict(compressed_bytes=len(raw), decompressed_bytes=len(unpacked),
                card_names=len(payload['data']), card_records=records)


def verify_receipt(archive, receipt_path, expected):
    receipt = strict_json(read_file(receipt_path, MAX_RECEIPT))
    if (not isinstance(receipt, dict) or receipt.get('schema_version') != 1
            or receipt.get('download_url') != BASE + ARCHIVE
            or receipt.get('checksum_url') != BASE + ARCHIVE + '.sha256'
            or receipt.get('sha256') != expected
            or not isinstance(receipt.get('version'), str)
            or not isinstance(receipt.get('verified_at_utc'), str)):
        raise ValueError('UNVERIFIED_OFFICIAL_SNAPSHOT_RECEIPT')
    observed = inspect_archive(archive, expected, receipt['version'])
    if any(receipt.get(k) != v for k, v in observed.items()):
        raise ValueError('SNAPSHOT_RECEIPT_CONTRADICTION')
    return receipt


def atomic_write(path, raw):
    safe_path(path)
    fd, name = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def setup(cache, *, offline=False):
    cache = safe_path(cache)
    cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not cache.is_dir():
        raise ValueError('CACHE_NOT_DIRECTORY')
    if os.name == 'posix' and (cache.stat().st_uid != os.getuid() or cache.stat().st_mode & 0o077):
        raise ValueError('CACHE_NOT_PRIVATE')
    current = cache / 'current.json'
    if offline:
        try:
            receipt = strict_json(read_file(current, MAX_RECEIPT))
            sha = receipt['sha256']
            if not isinstance(sha, str) or not re.fullmatch('[a-f0-9]{64}', sha):
                raise ValueError()
            archive = cache / (sha + '.json.gz')
            receipt_path = cache / (sha + '.receipt.json')
            verified = verify_receipt(archive, receipt_path, sha)
            if receipt != verified:
                raise ValueError()
        except (OSError, ValueError, KeyError, TypeError):
            raise ValueError('NO_VERIFIED_OFFLINE_CACHE') from None
        state = 'OFFLINE_VERIFIED_NOT_FRESHNESS_CHECKED'
    else:
        version, sha = upstream()
        archive = safe_path(cache / (sha + '.json.gz'))
        receipt_path = safe_path(cache / (sha + '.receipt.json'))
        try:
            verified = verify_receipt(archive, receipt_path, sha)
            if verified['version'] != version:
                raise ValueError('VERSION_CHANGED')
            state = 'REUSED_VERIFIED'
        except (OSError, ValueError, EOFError):
            with tempfile.TemporaryDirectory(prefix='.download-', dir=cache) as directory:
                pending = Path(directory) / ARCHIVE
                download(pending)
                coverage = inspect_archive(pending, sha, version)
                if upstream() != (version, sha):
                    raise ValueError('UPSTREAM_CHANGED_DURING_VERIFICATION')
                verified = dict(schema_version=1, version=version, sha256=sha,
                                download_url=BASE + ARCHIVE, checksum_url=BASE + ARCHIVE + '.sha256',
                                verified_at_utc=datetime.now(timezone.utc).isoformat(), **coverage)
                os.replace(pending, archive)
                archive.chmod(0o600)
                atomic_write(receipt_path, json.dumps(verified, sort_keys=True).encode())
            state = 'DOWNLOADED_VERIFIED'
        else:
            if upstream() != (version, sha):
                raise ValueError('UPSTREAM_CHANGED_DURING_VERIFICATION')
        atomic_write(current, json.dumps(verified, sort_keys=True).encode())
    return dict(verified, archive_path=str(archive), receipt_path=str(receipt_path),
                cache_status=state, status='RUNTIME_DATA_READY',
                limitations=['Local receipts are not authenticated signatures.',
                             'Offline mode verifies integrity, not current upstream freshness.'])
