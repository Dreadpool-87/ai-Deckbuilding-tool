#!/usr/bin/env python3
"""Read-only heuristic scan of reachable Git history; never print secret values.

This is NOT a guarantee that no private data exists in history, releases or logs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

SECRETS = {
    "github_token": re.compile(rb"(?:ghp_|gho_|ghs_|ghu_|ghr_)[A-Za-z0-9]{32,}|github_pat_[A-Za-z0-9_]{40,}"),
    "aws_access_key": re.compile(rb"AKIA[0-9A-Z]{16}"),
    "slack_token": re.compile(rb"xox[baprs]-[A-Za-z0-9-]{20,}"),
    "private_key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "credential_assignment": re.compile(
        rb"""(?im)(?:api[_-]?key|access[_-]?token|password|client[_-]?secret)
          \s*(?:=|:)\s*['"][^'"\r\n]{12,}['"]""", re.VERBOSE),
}
SENSITIVE_PATH = re.compile(
    r"(?i)(?:^|/)(?:\.env(?:\..+)?|[^/]*\.(?:pem|p12|pfx|key)|"
    r"[^/]*(?:private[_-]?key|secret[_-]?backup)[^/]*|"
    r"collections?|collecties|[^/]*(?:collection|collectie)[^/]*\.csv|"
    r"AtomicCards[^/]*\.json(?:\.gz)?|variants\.json\.gz)$"
)


def git(repo, *args, input_data=None):
    result = subprocess.run(["git", "-C", str(repo), *args],
                            input=input_data, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, check=False)
    if result.returncode:
        raise RuntimeError("git command failed: " + " ".join(args[:3]) +
                           " (exit " + str(result.returncode) + ")")
    return result.stdout


def scan(repo: Path, max_blob_bytes: int = 3_000_000) -> dict:
    raw_objects = git(repo, "rev-list", "--objects", "--all")
    names, shas = {}, []
    for row in raw_objects.decode("utf-8", errors="replace").splitlines():
        oid, _, path = row.partition(" ")
        shas.append(oid)
        if path:
            names.setdefault(oid, path)
    oids = list(dict.fromkeys(shas))
    check = git(repo, "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)",
                input_data=("\n".join(oids) + "\n").encode("ascii"))
    findings, skipped, examined = [], [], 0
    for line in check.decode("ascii", errors="replace").splitlines():
        oid, kind, size_str = line.split()
        if kind != "blob":
            continue
        path = names.get(oid, "(unknown blob path)")
        if SENSITIVE_PATH.search(path):
            findings.append({"kind": "sensitive_historical_path",
                             "path": path, "object": oid[:12]})
        size = int(size_str)
        if size > max_blob_bytes:
            skipped.append({"path": path, "object": oid[:12], "bytes": size})
            continue
        raw = git(repo, "cat-file", "blob", oid)
        examined += 1
        for kind, pattern in SECRETS.items():
            if pattern.search(raw):
                findings.append({"kind": kind, "path": path, "object": oid[:12]})
    messages = git(repo, "log", "--all", "--format=%B").split(b"\n")
    for kind, pattern in SECRETS.items():
        if pattern.search(b"\n".join(messages)):
            findings.append({"kind": kind, "path": "(commit message)", "object": None})
    return {
        "status": "POTENTIAL_ISSUES" if findings or skipped else "NO_PATTERN_HITS",
        "scope": "reachable blobs and commit messages in locally fetched refs only",
        "objects_enumerated": len(oids), "blobs_scanned": examined,
        "findings": findings, "blobs_too_large_to_scan": skipped,
        "limitations": [
            "Heuristic patterns do not prove absence of credentials or private data.",
            "GitHub Releases, Actions artifacts/logs, secrets and unreachable objects are not scanned.",
            "Use a full-history checkout (fetch-depth: 0) for meaningful results.",
            "No matched secret values are printed.",
        ],
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, default=Path("."))
    p.add_argument("--strict", action="store_true")
    args = p.parse_args(argv)
    result = scan(args.repo.resolve())
    print(json.dumps(result, indent=2))
    return 2 if args.strict and result["status"] != "NO_PATTERN_HITS" else 0


if __name__ == "__main__":
    sys.exit(main())
