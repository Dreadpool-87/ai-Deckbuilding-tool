#!/usr/bin/env python3
"""Small, read-only agent gateway over existing AI Deckbuilding Tool scripts.

No deck builder, no rules interpreter, no Swap Advisor recommendation API.
Source profiles are explicitly selected; no cross-environment automatic fallback.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
CARD_SEARCH = ROOT / "tools" / "card_search.py"
VALIDATOR = ROOT / "validator" / "MTG_Deck_Validator_v1.1.1.py"
ORACLE_PIN = "eb3c03c9303bbf17d50569320f0ab3a7a1d412511198805a36eec03cffff3468"
VALIDATOR_PIN = "f8e915a95e73e20edf59267dfe39e45f82d62bb5eb49fd4eb180194189d995ef"
CARD_SEARCH_PIN = "024de9aaaa1994ab6bce6944bd62e237f9fa9ea0ab52ed5b8bca8aca93a6851e"
VERSION = "0.3.0-experimental"
SCHEMA_VERSION = 1
DEFAULT_VALIDATOR_PROFILE = "github-main-v0.2"
VALIDATOR_PROFILES = {
    "github-main-v0.2": VALIDATOR_PIN,
    "project-prepare-candidate": "c422295676d0bad04aa1449725b07a7c11bf58b7990a34aff209e10ba742ac8d",
    "frozen-beta-20261022": "8749b50d0aeaa52124a99271a0ab40bcc979350c6e8b5e9074c4f28d63a3d1ac",
}
MAX_DATA = 128 * 1024 * 1024
MAX_SMALL = 4 * 1024 * 1024
MAX_STDOUT = 2 * 1024 * 1024


class GatewayError(Exception):
    def __init__(self, reason: str, *, executed: bool = False):
        super().__init__(reason)
        self.reason = reason
        # True only when the child script has actually been started.
        self.executed = executed


class _SafeParser(argparse.ArgumentParser):
    """Invalid CLI arguments must not leak user paths or break JSON output."""
    def error(self, message: str) -> None:
        raise GatewayError("INVALID_ARGUMENTS")


def _file(path: str | Path, max_bytes: int) -> Path:
    """Reject symlink paths (including symlinked parent directories)."""
    p = Path(path).absolute()
    if any(parent.is_symlink() for parent in (p, *p.parents)):
        raise GatewayError("UNSAFE_SYMLINK_PATH")
    try:
        info = p.stat()
    except OSError:
        raise GatewayError("REQUIRED_INPUT_UNAVAILABLE") from None
    if not stat.S_ISREG(info.st_mode) or info.st_size > max_bytes:
        raise GatewayError("INPUT_NOT_REGULAR_OR_TOO_LARGE")
    return p


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        raise GatewayError("SOURCE_READ_FAILED") from None
    return digest.hexdigest()


def _read_small_file(path: Path, max_bytes: int) -> bytes:
    """Read bounded, regular-file bytes from a no-follow file descriptor."""
    path = _file(path, max_bytes)
    flags = (os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
             | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0))
    try:
        with os.fdopen(os.open(path, flags), "rb") as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > max_bytes:
                raise GatewayError("INPUT_NOT_REGULAR_OR_TOO_LARGE")
            content = handle.read(max_bytes + 1)
    except OSError:
        raise GatewayError("SOURCE_READ_FAILED") from None
    if len(content) > max_bytes:
        raise GatewayError("INPUT_NOT_REGULAR_OR_TOO_LARGE")
    return content


def _pinned_script(path: Path, pin: str, mismatch: str) -> tuple[str, bytes]:
    """Bind a known code hash to the exact bytes later staged for execution."""
    content = _read_small_file(path, MAX_SMALL)
    digest = hashlib.sha256(content).hexdigest()
    if digest != pin:
        raise GatewayError(mismatch)
    return digest, content


def _validator_file(args: argparse.Namespace) -> tuple[Path, str, bytes]:
    """Select exactly one approved Validator and capture its executable bytes."""
    if args.validator_profile != DEFAULT_VALIDATOR_PROFILE and args.validator_file is None:
        raise GatewayError("EXPLICIT_VALIDATOR_FILE_REQUIRED")
    path = _file(args.validator_file or VALIDATOR, MAX_SMALL)
    digest, content = _pinned_script(
        path, VALIDATOR_PROFILES[args.validator_profile], "VALIDATOR_SHA256_MISMATCH")
    return path, digest, content


def _snapshot_input(source: Path, destination: Path, max_bytes: int) -> tuple[Path, str]:
    """Copy only bounded source bytes to a private snapshot; hash what was copied."""
    source = _file(source, max_bytes)
    flags = (os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
             | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0))
    digest = hashlib.sha256()
    total = 0
    try:
        with os.fdopen(os.open(source, flags), "rb") as original:
            info = os.fstat(original.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > max_bytes:
                raise GatewayError("INPUT_NOT_REGULAR_OR_TOO_LARGE")
            with destination.open("xb") as frozen:
                while True:
                    chunk = original.read(min(1024 * 1024, max_bytes - total + 1))
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        raise GatewayError("INPUT_NOT_REGULAR_OR_TOO_LARGE")
                    frozen.write(chunk)
                    digest.update(chunk)
        # Verify the bytes on disk, not only those supplied by the caller.
        if _sha(destination) != digest.hexdigest():
            raise GatewayError("INPUT_SNAPSHOT_VERIFICATION_FAILED")
    except OSError:
        raise GatewayError("INPUT_SNAPSHOT_FAILED") from None
    return destination, digest.hexdigest()


def _stage_verified_script(destination: Path, content: bytes, expected: str) -> Path:
    """Execute only bytes already checked against a hardcoded source pin."""
    try:
        destination.write_bytes(content)
        destination.chmod(0o600)
        if _sha(destination) != expected:
            raise GatewayError("CODE_STAGING_VERIFICATION_FAILED")
    except OSError:
        raise GatewayError("CODE_STAGING_FAILED") from None
    return destination


def _unchanged(paths: tuple[tuple[Path, str, int], ...]) -> None:
    """Reject detectable source changes between validation and child completion."""
    try:
        for path, expected, max_bytes in paths:
            if _sha(_file(path, max_bytes)) != expected:
                raise GatewayError("SOURCE_CHANGED_DURING_EXECUTION", executed=True)
    except GatewayError as exc:
        raise GatewayError("SOURCE_CHANGED_DURING_EXECUTION", executed=True) from None


def _sources(args: argparse.Namespace, stage: Path, *, validate: bool
             ) -> tuple[Path, Path, Path | None, dict, tuple]:
    """Snapshot all child-tool inputs, verifying the Oracle snapshot itself."""
    original_oracle = _file(args.oracle, MAX_DATA)
    original_collection = _file(args.collection, MAX_SMALL)
    original_deck = _file(args.deck, MAX_SMALL) if validate else None
    if not re.fullmatch(r"[0-9a-f]{64}", args.oracle_sha256):
        raise GatewayError("INVALID_EXPECTED_ORACLE_SHA256")
    oracle_name = "oracle.json.gz" if original_oracle.suffix.lower() == ".gz" else "oracle.json"
    oracle, observed = _snapshot_input(original_oracle, stage / oracle_name, MAX_DATA)
    if observed != args.oracle_sha256:
        raise GatewayError("ORACLE_SHA256_MISMATCH")
    if args.collection_scope == "current-run-confirmed" and observed != ORACLE_PIN:
        raise GatewayError("ACTIVE_ORACLE_PIN_UNSUPPORTED")
    collection, collection_hash = _snapshot_input(
        original_collection, stage / "collection.csv", MAX_SMALL)
    deck, deck_hash = ((None, None) if original_deck is None else
                       _snapshot_input(original_deck, stage / "deck.txt", MAX_SMALL))
    tracked = ((original_oracle, observed, MAX_DATA),
               (original_collection, collection_hash, MAX_SMALL))
    if original_deck is not None:
        tracked += ((original_deck, deck_hash, MAX_SMALL),)
    return oracle, collection, deck, {
        "oracle_sha256": observed,
        "oracle_pin_basis": ("FROZEN_SLIM_PIN" if observed == ORACLE_PIN
                             else "CALLER_SPECIFIED_SYNTHETIC_TEST_PIN"),
        "collection_scope": args.collection_scope,
        "collection_sha256": collection_hash,
        "deck_sha256": deck_hash,
        "ownership_authentication": "NOT_IMPLEMENTED",
    }, tracked


def _distinct_json_object(pairs: list[tuple[str, object]]) -> dict:
    """Reject contradictory duplicate keys at any child-JSON nesting level."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise GatewayError("SUBPROCESS_DUPLICATE_JSON_KEY", executed=True)
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise GatewayError("SUBPROCESS_NONFINITE_JSON_NUMBER", executed=True)


def _run(script: Path, args: list[str]) -> tuple[int, dict]:
    script = _file(script, MAX_SMALL)
    try:
        completed = subprocess.run(
            [sys.executable, "-B", str(script), *args],
            cwd=str(ROOT), capture_output=True, timeout=90, check=False,
        )
    except subprocess.TimeoutExpired:
        raise GatewayError("SUBPROCESS_TIMED_OUT", executed=True) from None
    except OSError:
        raise GatewayError("SUBPROCESS_NOT_STARTED") from None
    if len(completed.stdout) > MAX_STDOUT or len(completed.stderr) > 128 * 1024:
        raise GatewayError("SUBPROCESS_OUTPUT_TOO_LARGE", executed=True)
    try:
        payload = json.loads(completed.stdout.decode("utf-8"),
                             object_pairs_hook=_distinct_json_object,
                             parse_constant=_reject_json_constant)
    except (UnicodeError, ValueError):
        raise GatewayError("SUBPROCESS_JSON_INVALID", executed=True) from None
    if not isinstance(payload, dict):
        raise GatewayError("SUBPROCESS_SCHEMA_INVALID", executed=True)
    return completed.returncode, payload


def _doctor(args: argparse.Namespace) -> tuple[str, dict]:
    if args.validator_profile != DEFAULT_VALIDATOR_PROFILE and args.validator_file is None:
        raise GatewayError("EXPLICIT_VALIDATOR_FILE_REQUIRED")
    chosen = args.validator_file or VALIDATOR
    checks = {}
    for label, path, expected in (("card_search", CARD_SEARCH, CARD_SEARCH_PIN),
                                  ("validator", chosen,
                                   VALIDATOR_PROFILES[args.validator_profile])):
        try:
            # Read the exact bounded bytes; no caller-provided pin overrides.
            digest = hashlib.sha256(_read_small_file(path, MAX_SMALL)).hexdigest()
            checks[label] = {"status": "AVAILABLE", "sha256": digest,
                             "pin_matches": digest == expected}
        except GatewayError as exc:
            checks[label] = {"status": "UNAVAILABLE", "reason": exc.reason,
                             "pin_matches": False}
    checks["validator"]["profile"] = args.validator_profile
    if args.oracle is not None:
        try:
            item = _file(args.oracle, MAX_DATA)
            digest = _sha(item)
            checks["oracle"] = {
                "status": "FILE_READABLE_NOT_RULES_VERIFIED",
                "sha256": digest, "matches_slim_pin": digest == ORACLE_PIN,
            }
        except GatewayError as exc:
            checks["oracle"] = {"status": "UNAVAILABLE", "reason": exc.reason}
    ready = (checks["card_search"]["pin_matches"]
             and checks["validator"]["pin_matches"]
             and ("oracle" not in checks or checks["oracle"].get("matches_slim_pin") is True))
    return ("RUNTIME_COMPONENTS_PRESENT" if ready else "UNVERIFIED"), {
        "validator_profile": args.validator_profile,
        "checks": checks,
        "limitations": [
            "Doctor verifies selected local source hashes, not complete rules or card validity.",
            "No collection authenticity, deck quality, or real swap capability is established.",
        ],
    }


def _dispatch(args: argparse.Namespace) -> tuple[str, dict]:
    if args.action == "doctor":
        return _doctor(args)
    if args.collection_scope == "current-run-confirmed" and not args.collection_confirmed:
        raise GatewayError("COLLECTION_CONFIRMATION_REQUIRED")
    if args.collection_scope == "synthetic" and args.collection_confirmed:
        raise GatewayError("CONTRADICTORY_COLLECTION_SCOPE")

    # Capture executable bytes before opening user inputs. Neither code pin can
    # be overridden by CLI input, and only the captured bytes run.
    selected_validator, selected_validator_sha, validator_bytes = (
        _validator_file(args) if args.action == "validate" else (None, None, None))
    card_search_bytes = None
    if args.action == "discover":
        card_search_sha, card_search_bytes = _pinned_script(
            CARD_SEARCH, CARD_SEARCH_PIN, "CARD_SEARCH_SHA256_MISMATCH")

    try:
        with tempfile.TemporaryDirectory(prefix="mtg-agent-gateway-") as directory:
            stage = Path(directory)
            oracle, collection, deck, context, tracked = _sources(
                args, stage, validate=args.action == "validate")
            if selected_validator is not None:
                context["validator_profile"] = args.validator_profile
                context["validator_sha256"] = selected_validator_sha
            if args.action == "discover":
                if not 1 <= args.limit <= 100 or not 0 <= args.offset <= 1000000:
                    raise GatewayError("INVALID_SEARCH_BOUNDS")
                command = [
                    "--oracle", str(oracle), "--collection", str(collection),
                    "--owned-only", "--theme", args.theme, "--limit", str(args.limit),
                    "--offset", str(args.offset), "--format", "json",
                ]
                if args.identity:
                    command.extend(("--identity", args.identity))
                verified_search = _stage_verified_script(
                    stage / "card_search.py", card_search_bytes, card_search_sha)
                rc, data = _run(verified_search, command)
                _unchanged(tracked + ((CARD_SEARCH, card_search_sha, MAX_SMALL),))
                if rc != 0 or not isinstance(data.get("results"), list) or "coverage" not in data:
                    raise GatewayError("DISCOVERY_FAILED_OR_SCHEMA_UNEXPECTED", executed=True)
                data.pop("oracle_file", None)  # Never expose snapshot paths.
                return "CANDIDATES_NOT_VALIDATED", {
                    **context, "result": data, "limitations": [
                        "Search matches and role labels are heuristics, not legal deck or swap proof.",
                        "Ownership is supplied by the caller; current-run consent is not cryptographically authenticated.",
                    ],
                }
            command = [
                "--oracle", str(oracle), "--collection", str(collection),
                "--deck", str(deck), "--mode", "casual",
            ]
            if args.exact_60:
                command.append("--exact-60")
            verified_validator = _stage_verified_script(
                stage / "validator.py", validator_bytes, selected_validator_sha)
            rc, data = _run(verified_validator, command)
            _unchanged(tracked + ((selected_validator, selected_validator_sha, MAX_SMALL),))
            allowed = {"PASS_WITH_LIMITATIONS": 0, "FAIL": 1, "UNVERIFIED": 3}
            status = data.get("status")
            if status not in allowed or rc != allowed[status]:
                raise GatewayError("VALIDATOR_STATUS_EXIT_CONTRADICTION", executed=True)
            for field in ("source_collection", "source_oracle", "source_deck"):
                data.pop(field, None)
            return ({
                "PASS_WITH_LIMITATIONS": "VALIDATED_WITH_LIMITATIONS",
                "FAIL": "BLOCKED_INVALID_DECK",
                "UNVERIFIED": "UNVERIFIED",
            }[status], {
                **context, "result": data,
                "limitations": [
                    "This checks the stated deck and declared collection; collection confirmation is not authenticated.",
                    "Validation is not proof of strategic superiority, full legality, gameplay or castability.",
                ],
            })
    except OSError:
        raise GatewayError("INPUT_OR_STAGING_FAILED") from None


def _parser() -> argparse.ArgumentParser:
    p = _SafeParser(description=__doc__, allow_abbrev=False)
    subs = p.add_subparsers(dest="action", required=True, parser_class=_SafeParser)
    doctor = subs.add_parser("doctor", allow_abbrev=False)
    doctor.add_argument("--oracle")
    doctor.add_argument("--validator-file")
    doctor.add_argument("--validator-profile", choices=tuple(VALIDATOR_PROFILES),
                        default=DEFAULT_VALIDATOR_PROFILE)
    for action in ("discover", "validate"):
        sub = subs.add_parser(action, allow_abbrev=False)
        sub.add_argument("--oracle", required=True)
        sub.add_argument("--oracle-sha256", default=ORACLE_PIN)
        sub.add_argument("--collection", required=True)
        sub.add_argument("--collection-scope", choices=("synthetic", "current-run-confirmed"), required=True)
        sub.add_argument("--collection-confirmed", action="store_true")
        if action == "discover":
            sub.add_argument("--theme", required=True)
            sub.add_argument("--identity")
            sub.add_argument("--limit", type=int, default=50)
            sub.add_argument("--offset", type=int, default=0)
        else:
            sub.add_argument("--validator-file")
            sub.add_argument("--validator-profile", choices=tuple(VALIDATOR_PROFILES),
                             default=DEFAULT_VALIDATOR_PROFILE)
            sub.add_argument("--deck", required=True)
            sub.add_argument("--exact-60", action="store_true")
    return p


def _result_envelope(action: str, status: str, executed: bool, info: dict,
                     *, execution_failed: bool = False) -> dict:
    """Add the common read-only v1 result contract without changing P2 payloads."""
    if executed and action == "doctor":
        raise ValueError("Doctor cannot claim downstream execution")
    if execution_failed and not executed:
        raise ValueError("Cannot report failed execution without a started child")
    oracle_sha = info.get("oracle_sha256")
    validator_sha = info.get("validator_sha256")
    collection_sha = info.get("collection_sha256")
    deck_sha = info.get("deck_sha256")
    checks = info.get("checks")
    if isinstance(checks, dict):
        oracle_sha = (checks.get("oracle") or {}).get("sha256", oracle_sha)
        validator_sha = (checks.get("validator") or {}).get("sha256", validator_sha)
    sources = {
        "oracle_sha256": oracle_sha,
        "validator_sha256": validator_sha,
        "validator_profile": info.get("validator_profile"),
        "collection_sha256": collection_sha,
        "deck_sha256": deck_sha,
        "collection_scope": info.get("collection_scope"),
        "ownership_authentication": info.get(
            "ownership_authentication", "NOT_CHECKED" if action == "doctor" else "NOT_IMPLEMENTED"),
    }
    facts, derivations, hypotheses = [], [], []
    uncertainties, reasons = [], []
    if "reason" in info:
        reasons.append(info["reason"])
        uncertainties.extend(("NO_TRUSTED_RESULT", "SWAP_NOT_ASSESSED"))
    elif action == "doctor":
        derivations.append({
            "code": "LOCAL_COMPONENT_READINESS", "basis": "LOCAL_FILE_CHECK",
            "scope": "PRESENCE_AND_RECORDED_SHA_ONLY",
        })
        uncertainties.extend(("DECK_NOT_VALIDATED", "OWNERSHIP_NOT_AUTHENTICATED",
                              "STRATEGIC_IMPROVEMENT_UNVERIFIED"))
        if "oracle" not in (checks or {}):
            uncertainties.append("ORACLE_NOT_CHECKED")
        if status == "UNVERIFIED":
            reasons.append("LOCAL_COMPONENTS_UNVERIFIED")
    else:
        if oracle_sha is not None:
            facts.append({
                "code": "ORACLE_FILE_SHA256_MATCHED_REQUEST", "basis": "LOCAL_SHA256",
                "scope": "INPUT_FILE_BYTES_NOT_CARD_RULES_PROOF",
            })
        uncertainties.extend(("OWNERSHIP_CONFIRMATION_NOT_AUTHENTICATED",
                              "STRATEGIC_IMPROVEMENT_UNVERIFIED"))
        child = info.get("result") or {}
        if action == "discover":
            hypotheses.append({
                "code": "DISCOVERED_CARD_ROLES", "basis": "CARD_SEARCH_V0_3",
                "scope": "HEURISTIC_NOT_RULES_VERIFIED",
            })
            uncertainties.append("CANDIDATES_NOT_DECK_VALIDATED")
            if (child.get("collection_coverage") or {}).get("unresolved_name_count", 0):
                uncertainties.append("ORACLE_COLLECTION_COVERAGE_INCOMPLETE")
        elif action == "validate":
            derivations.append({
                "code": "CASUAL_VALIDATOR_OUTCOME", "basis": "PINNED_EXPLICIT_VALIDATOR_PROFILE",
                "scope": "STRUCTURAL_VALIDATION_ONLY",
            })
            uncertainties.extend(("FULL_RULES_NOT_VERIFIED", "SWAP_NOT_ASSESSED"))
            if status == "BLOCKED_INVALID_DECK":
                reasons.append("VALIDATOR_REJECTED_DECK")
            elif status == "UNVERIFIED":
                reasons.append("VALIDATOR_REPORTED_UNVERIFIED")
                uncertainties.append("VALIDATOR_REPORTED_UNVERIFIED")
    tool_execution = ("FAILED_AFTER_START" if execution_failed else
                      "EXECUTED" if executed else "NOT_EXECUTED")
    # P2-specific fields remain for callers. The top-level status is authoritative;
    # the nested result.status is an unmodified child-tool outcome, not a second decision.
    return {
        "schema_version": SCHEMA_VERSION, "gateway_version": VERSION,
        "action": action, "status": status, "executed": executed,
        "tool_execution": tool_execution, "sources": sources,
        "evidence": {"facts": facts, "derivations": derivations,
                     "hypotheses": hypotheses},
        "reason_codes": reasons, "uncertainties": sorted(set(uncertainties)),
        "limitations": list(info.get("limitations", [])),
        "automatic_swap_authorized": False,
        "strategic_improvement_verified": False,
        **info,
    }


def main(argv: list[str] | None = None) -> int:
    supplied = sys.argv[1:] if argv is None else argv
    safe_action = supplied[0] if supplied and supplied[0] in ("doctor", "discover", "validate") else "UNKNOWN"
    try:
        args = _parser().parse_args(supplied)
        status, info = _dispatch(args)
        report = _result_envelope(args.action, status, args.action != "doctor", info)
        code = (0 if status in ("RUNTIME_COMPONENTS_PRESENT", "CANDIDATES_NOT_VALIDATED",
                                "VALIDATED_WITH_LIMITATIONS") else
                3 if status == "UNVERIFIED" else 2)
    except GatewayError as exc:
        status = ("UNVERIFIED" if exc.executed or exc.reason == "SUBPROCESS_NOT_STARTED"
                  else "INPUT_ERROR")
        info = {"reason": exc.reason,
                "limitations": ["No trusted result can be inferred from a failed command."]}
        report = _result_envelope(safe_action, status, exc.executed, info,
                                  execution_failed=exc.executed)
        code = 3 if status == "UNVERIFIED" else 2
    print(json.dumps(report, sort_keys=True, ensure_ascii=False, allow_nan=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
