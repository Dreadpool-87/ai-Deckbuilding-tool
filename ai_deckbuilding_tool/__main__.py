"""One-command, fail-closed adapter to the existing verified Agent Gateway.

Automatic official data preparation; no card selection or strategic ranking.
Run 'python -m ai_deckbuilding_tool --help' from a local repository checkout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MAX_SOURCE_BYTES = 4 * 1024 * 1024
COLLECTION_IMPORT_PIN = "72eeefbadb861916dc3a21e1fecf3334a9a33da2bb7659b6192a0c28ae268d5f"
PINNED_CODE = {
    "tools/agent_gateway.py": "4382664a19d8f9ec0743980b2cd8128d2311099df29e9145e047156ccaee90a9",
    "tools/atomic_runtime.py": "afe61cacf143a6197fd99f36fa388c73105ac55dbaac8abe30d883f9cf84fe59",
    "tools/card_search.py": "fc90135092476419ab3254c3142d1a8a9df6420e5ad80b54a7180b46822fbc82",
    "tools/card_identity.py": "c4aa79b6f9341f9c0fe5d775b267ec7d4b5e371edf1dfcb99a9eaf644104d239",
    "validator/MTG_Deck_Validator_v1.1.1.py": "58b1015c1138b6bb5bfb2b49cd1762d56ea9cc4687d9e87314f2124570a0a5fd",
}
MAX_GATEWAY_OUTPUT = 2 * 1024 * 1024
TIMEOUT_SECONDS = 120
KNOWN_STATUSES = {
    "doctor": {"RUNTIME_COMPONENTS_PRESENT": 0, "UNVERIFIED": 3, "INPUT_ERROR": 2},
    "discover": {"CANDIDATES_NOT_VALIDATED": 0, "UNVERIFIED": 3, "INPUT_ERROR": 2},
    "validate": {
        "VALIDATED_WITH_LIMITATIONS": 0,
        "BLOCKED_INVALID_DECK": 2,
        "UNVERIFIED": 3,
        "INPUT_ERROR": 2,
    },
}


class SafeParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError("INVALID_ARGUMENTS")


def _reject_constant(value: str) -> None:
    raise ValueError("NONFINITE_JSON")


def _gateway(action: str, flags: list[str]) -> tuple[int, dict]:
    # Run SHA-checked copies, not a mutable repository file or host startup hook.
    # The original Gateway performs its own input snapshots and child-code pinning.
    with tempfile.TemporaryDirectory(prefix="ai-deckbuilding-cli-") as directory:
        stage = Path(directory)
        for relative, expected in PINNED_CODE.items():
            source = ROOT / relative
            try:
                if any(parent.is_symlink() for parent in (source, *source.parents)):
                    raise RuntimeError("UNSAFE_LOCAL_CODE_SOURCE")
                if not source.is_file() or source.stat().st_size > MAX_SOURCE_BYTES:
                    raise RuntimeError("LOCAL_CODE_SOURCE_UNAVAILABLE")
                content = source.read_bytes()
            except OSError:
                raise RuntimeError("LOCAL_CODE_SOURCE_UNAVAILABLE") from None
            if (len(content) > MAX_SOURCE_BYTES
                    or hashlib.sha256(content).hexdigest() != expected):
                raise RuntimeError("LOCAL_CODE_SHA256_MISMATCH")
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            target.chmod(0o600)
        try:
            completed = subprocess.run(
                [sys.executable, "-I", "-S", "-B", "-Xutf8",
                 str(stage / "tools" / "agent_gateway.py"), action, *flags],
                cwd=stage, stdin=subprocess.DEVNULL, capture_output=True,
                timeout=TIMEOUT_SECONDS, check=False,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("GATEWAY_TIMEOUT") from None
        except OSError:
            raise RuntimeError("GATEWAY_NOT_STARTED") from None
    if len(completed.stdout) > MAX_GATEWAY_OUTPUT:
        raise RuntimeError("GATEWAY_OUTPUT_TOO_LARGE")
    try:
        result = json.loads(completed.stdout.decode("utf-8"),
                            parse_constant=_reject_constant)
    except (UnicodeError, ValueError, RecursionError):
        raise RuntimeError("GATEWAY_JSON_UNTRUSTED") from None
    if (not isinstance(result, dict) or result.get("schema_version") != 1
            or result.get("action") != action
            or result.get("status") not in KNOWN_STATUSES[action]
            or completed.returncode != KNOWN_STATUSES[action][result["status"]]
            or type(result.get("executed")) is not bool
            or result.get("tool_execution") not in
                ("NOT_EXECUTED", "EXECUTED", "FAILED_AFTER_START")
            or result["executed"] !=
                (result["tool_execution"] != "NOT_EXECUTED")
            or not isinstance(result.get("reason_codes"), list)):
        raise RuntimeError("GATEWAY_RESULT_UNTRUSTED")
    if (action == "doctor" and result["executed"]
            or action != "doctor" and result["status"] in
                ("CANDIDATES_NOT_VALIDATED", "VALIDATED_WITH_LIMITATIONS",
                 "BLOCKED_INVALID_DECK") and not result["executed"]):
        raise RuntimeError("GATEWAY_EXECUTION_CONTRADICTION")
    return completed.returncode, result


def _parser() -> argparse.ArgumentParser:
    parser = SafeParser(description=__doc__, allow_abbrev=False)
    commands = parser.add_subparsers(dest="action", required=True,
                                    parser_class=SafeParser)
    doctor = commands.add_parser("doctor", allow_abbrev=False)
    doctor.add_argument("--oracle-receipt")
    doctor.add_argument("--oracle", help="Local pinned slim Oracle (optional for source-only check)")
    for action in ("discover", "validate"):
        sub = commands.add_parser(action, allow_abbrev=False)
        sub.add_argument("--oracle")
        sub.add_argument("--oracle-receipt")
        sub.add_argument("--offline", action="store_true")
        sub.add_argument("--cache-dir", type=Path)
        sub.add_argument("--collection", required=True)
        sub.add_argument("--oracle-sha256",
                         help="Explicit digest required for synthetic fixtures; real mode uses the Gateway pin")
        sub.add_argument("--synthetic", action="store_true",
                         help="Synthetic test fixtures only, never for real user collections")
        sub.add_argument("--collection-confirmed", action="store_true",
                         help="Declare user's explicit confirmation for this execution")
        if action == "discover":
            sub.add_argument("--theme", required=True)
        else:
            sub.add_argument("--deck", required=True)
            sub.add_argument("--allow-over-60", action="store_true",
                             help="Permit Casual 60+ instead of requiring exactly 60")
    setup = commands.add_parser('setup', allow_abbrev=False)
    setup.add_argument('--offline', action='store_true')
    setup.add_argument('--cache-dir', type=Path)
    return parser


def _report(action: str, status: str, *, reason: str | None = None,
            preflight: dict | None = None, gateway: dict | None = None,
            next_action: str, validated: bool = False) -> dict:
    return {
        "schema_version": 1,
        "action": action,
        "status": status,
        "reason_codes": [] if reason is None else [reason],
        "preflight": preflight,
        "gateway": gateway,
        "validated": validated,
        "next_action": next_action,
        "limitations": [
            "Only an executed pinned Gateway Validator can verify structural deck checks.",
            "No deck strategy, gameplay, full format legality or win rate is certified.",
            "Setup uses official upstream data; private collections are never uploaded.",
        ],
    }


def _run_prepared(args: argparse.Namespace) -> tuple[int, dict]:
    # Resolve user inputs before the Gateway runs from a private staged checkout.
    for field in ("oracle", "collection", "deck"):
        value = getattr(args, field, None)
        if value:
            setattr(args, field, str(Path(value).absolute()))
    # The Gateway's doctor validates the local Python/scripts and, in real mode,
    # the original pinned Oracle bytes before the requested action can start.
    doctor_flags = ["--oracle", args.oracle] if args.oracle and not getattr(args, "synthetic", False) else []
    if getattr(args, 'oracle_receipt', None) and doctor_flags:
        doctor_flags += ['--oracle-receipt', str(Path(args.oracle_receipt).absolute())]
    _, doctor = _gateway("doctor", doctor_flags)
    if doctor["status"] != "RUNTIME_COMPONENTS_PRESENT":
        return 3, _report(args.action, "UNVERIFIED", reason="PREFLIGHT_UNVERIFIED",
                          preflight=doctor, next_action="REPAIR_RUNTIME_OR_ORACLE")
    if args.action == "doctor":
        if not args.oracle:
            return 3, _report("doctor", "UNVERIFIED", reason="PINNED_ORACLE_NOT_SUPPLIED",
                              preflight=doctor, next_action="PROVIDE_PINNED_ORACLE")
        return 0, _report("doctor", "RUNTIME_READY", preflight=doctor,
                          next_action="PROVIDE_CONFIRMED_COLLECTION")
    if not args.synthetic and not args.collection_confirmed:
        return 2, _report(args.action, "INPUT_ERROR",
                          reason="CURRENT_RUN_COLLECTION_CONFIRMATION_REQUIRED",
                          preflight=doctor, next_action="CONFIRM_COLLECTION_FOR_THIS_RUN")
    if args.synthetic and args.collection_confirmed:
        return 2, _report(args.action, "INPUT_ERROR",
                          reason="SYNTHETIC_COLLECTION_CANNOT_BE_CONFIRMED",
                          preflight=doctor, next_action="FIX_COLLECTION_SCOPE")
    if args.synthetic and not args.oracle_sha256:
        return 2, _report(args.action, "INPUT_ERROR",
                          reason="SYNTHETIC_ORACLE_DIGEST_REQUIRED",
                          preflight=doctor, next_action="PROVIDE_FIXTURE_SHA256")

    flags = ["--oracle", args.oracle, "--collection", args.collection,
             "--collection-scope",
             "synthetic" if args.synthetic else "current-run-confirmed"]
    if getattr(args, 'oracle_receipt', None):
        flags += ['--oracle-receipt', str(Path(args.oracle_receipt).absolute())]
    if args.oracle_sha256:
        flags += ["--oracle-sha256", args.oracle_sha256]
    if args.collection_confirmed:
        flags.append("--collection-confirmed")
    if args.action == "discover":
        flags += ["--theme", args.theme]
    else:
        flags += ["--deck", args.deck]
        if not args.allow_over_60:
            flags.append("--exact-60")

    code, result = _gateway(args.action, flags)
    status = result["status"]
    return code, _report(
        args.action, status, preflight=doctor, gateway=result,
        reason=(result["reason_codes"][0] if result["reason_codes"] else None),
        validated=status == "VALIDATED_WITH_LIMITATIONS",
        next_action=(
            "AI_BUILD_AND_SUBMIT_DECK" if status == "CANDIDATES_NOT_VALIDATED"
            else "AI_REVIEW_VALIDATED_DECK" if status == "VALIDATED_WITH_LIMITATIONS"
            else "AI_REVISE_DECK_AND_REVALIDATE" if status == "BLOCKED_INVALID_DECK"
            else "INSPECT_GATEWAY_FAILURE_AND_REPAIR"
        ),
    )


def _atomic_support():
    source = ROOT / 'tools/atomic_runtime.py'
    if any(p.is_symlink() for p in (source, *source.parents)) or not source.is_file():
        raise RuntimeError('LOCAL_CODE_SOURCE_UNAVAILABLE')
    raw = source.read_bytes()
    if len(raw) > MAX_SOURCE_BYTES or hashlib.sha256(raw).hexdigest() != PINNED_CODE['tools/atomic_runtime.py']:
        raise RuntimeError('LOCAL_CODE_SHA256_MISMATCH')
    support = {'__name__': 'cli_atomic_support'}
    exec(compile(raw, str(source), 'exec'), support)
    return support


def run(args):
    if sys.version_info < (3, 12):
        raise RuntimeError('PYTHON_3_12_REQUIRED')
    runtime = None
    if args.action == 'setup' or (args.action in ('discover', 'validate') and not args.oracle):
        # Verify executable components before any network or private input access.
        _, doctor = _gateway('doctor', [])
        if doctor['status'] != 'RUNTIME_COMPONENTS_PRESENT':
            raise RuntimeError('PREFLIGHT_UNVERIFIED')
        cache = getattr(args, 'cache_dir', None) or Path.home() / '.cache' / 'ai-deckbuilding-tool' / 'atomic'
        try:
            runtime = _atomic_support()['setup'](cache, offline=args.offline)
        except (OSError, ValueError, EOFError) as exc:
            reason = str(exc) if isinstance(exc, ValueError) and str(exc).isupper() else 'OFFICIAL_DATA_SETUP_FAILED'
            raise RuntimeError(reason) from None
        if args.action == 'setup':
            return 0, dict(schema_version=1, action='setup', status='RUNTIME_READY',
                           validated=False, runtime=runtime, preflight=doctor,
                           next_action='SUPPLY_CONFIRMED_COLLECTION_AND_DISCOVER')
        args.oracle, args.oracle_sha256 = runtime['archive_path'], runtime['sha256']
        args.oracle_receipt = runtime['receipt_path']
    if args.action == 'doctor':
        return _run_prepared(args)
    import_code = (ROOT / 'ai_deckbuilding_tool/collection_import.py').read_bytes()
    if hashlib.sha256(import_code).hexdigest() != COLLECTION_IMPORT_PIN:
        raise RuntimeError('COLLECTION_IMPORT_SOURCE_MISMATCH')
    importer = {'__name__': 'pinned_collection_import'}
    exec(compile(import_code, '<pinned collection import>', 'exec'), importer)
    normalize = importer['normalize']
    support = _atomic_support()
    try:
        original_path = Path(args.collection).absolute()
        raw = support['read_file'](original_path, MAX_SOURCE_BYTES)
        normalized, evidence = normalize(raw)
        with tempfile.TemporaryDirectory(prefix='ai-deckbuilding-collection-') as directory:
            path = Path(directory) / 'collection.csv'
            path.write_bytes(normalized)
            path.chmod(0o600)
            args.collection = str(path)
            code, report = _run_prepared(args)
            if support['read_file'](original_path, MAX_SOURCE_BYTES) != raw:
                raise RuntimeError('COLLECTION_CHANGED_DURING_EXECUTION')
            report['collection_import'] = evidence
            if runtime is not None:
                report['runtime'] = runtime
            return code, report
    except (OSError, ValueError):
        raise RuntimeError('COLLECTION_IMPORT_FAILED') from None


def main(argv: list[str] | None = None) -> int:
    supplied = sys.argv[1:] if argv is None else argv
    action = supplied[0] if supplied and supplied[0] in (*KNOWN_STATUSES, "setup") else "UNKNOWN"
    try:
        args = _parser().parse_args(supplied)
        code, report = run(args)
    except ValueError:
        code, report = 2, _report(action, "INPUT_ERROR", reason="INVALID_ARGUMENTS",
                                   next_action="FIX_COMMAND_ARGUMENTS")
    except RuntimeError as exc:
        code, report = 3, _report(action, "UNVERIFIED", reason=str(exc),
                                   next_action="REPAIR_GATEWAY_EXECUTION")
    print(json.dumps(report, sort_keys=True, allow_nan=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
