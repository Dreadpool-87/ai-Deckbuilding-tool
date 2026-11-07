"""One-command, fail-closed adapter to the existing verified Agent Gateway.

No network downloads, card selection, strategic ranking or validator replacement.
Run 'python -m ai_deckbuilding_tool --help' from a local repository checkout.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
GATEWAY = ROOT / "tools" / "agent_gateway.py"
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
    if not GATEWAY.is_file():
        raise RuntimeError("GATEWAY_FILE_MISSING")
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-S", "-B", "-Xutf8", str(GATEWAY), action, *flags],
            cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True,
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
    doctor.add_argument("--oracle", help="Local pinned slim Oracle (optional for source-only check)")
    for action in ("discover", "validate"):
        sub = commands.add_parser(action, allow_abbrev=False)
        sub.add_argument("--oracle", required=True)
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
            "No network setup, collection upload or Oracle download is performed.",
        ],
    }


def run(args: argparse.Namespace) -> tuple[int, dict]:
    # The Gateway's doctor validates the local Python/scripts and, in real mode,
    # the original pinned Oracle bytes before the requested action can start.
    doctor_flags = ["--oracle", args.oracle] if args.oracle and not getattr(args, "synthetic", False) else []
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


def main(argv: list[str] | None = None) -> int:
    supplied = sys.argv[1:] if argv is None else argv
    action = supplied[0] if supplied and supplied[0] in KNOWN_STATUSES else "UNKNOWN"
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
