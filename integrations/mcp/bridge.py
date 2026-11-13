"""Small, SDK-independent adapter to the existing AI Deckbuilding Tool CLI.

This module does not build decks, interpret card rules, or claim validation.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
MAX_COLLECTION_BYTES = 4 * 1024 * 1024
MAX_DECK_BYTES = 256 * 1024
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
TIMEOUT_SECONDS = 240
VALID_STATUSES = {
    "discover": {0: {"CANDIDATES_NOT_VALIDATED"}, 2: {"INPUT_ERROR"}, 3: {"UNVERIFIED"}},
    "validate": {0: {"VALIDATED_WITH_LIMITATIONS"},
                 2: {"BLOCKED_INVALID_DECK", "INPUT_ERROR"}, 3: {"UNVERIFIED"}},
}


def blocked(action: str, reason: str, *, launched: bool = False) -> dict:
    return {
        "action": action, "status": "UNVERIFIED", "validated": False,
        "tool_execution": "FAILED_AFTER_START" if launched else "NOT_EXECUTED",
        "reason_codes": [reason],
        "next_action": "CORRECT_INPUT_OR_CHECK_RUNTIME",
    }


def execute(action: str, collection_csv: str, *, confirmed: bool,
            theme: str | None = None, decklist: str | None = None,
            offline: bool = False) -> dict:
    """Pass private in-memory inputs to the pinned CLI, return only actual output."""
    if action not in VALID_STATUSES:
        raise ValueError("UNSUPPORTED_ACTION")
    if confirmed is not True:
        return blocked(action, "CURRENT_RUN_COLLECTION_CONFIRMATION_REQUIRED")
    if type(collection_csv) is not str or not collection_csv.strip():
        return blocked(action, "COLLECTION_REQUIRED")
    collection = collection_csv.encode("utf-8")
    if len(collection) > MAX_COLLECTION_BYTES:
        return blocked(action, "COLLECTION_TOO_LARGE")
    if action == "discover":
        if type(theme) is not str or not theme.strip() or len(theme.encode("utf-8")) > 256:
            return blocked(action, "THEME_REQUIRED_OR_TOO_LONG")
    else:
        if type(decklist) is not str or not decklist.strip():
            return blocked(action, "DECK_REQUIRED")
        if len(decklist.encode("utf-8")) > MAX_DECK_BYTES:
            return blocked(action, "DECK_TOO_LARGE")
    with tempfile.TemporaryDirectory(prefix="mtg-mcp-") as temporary:
        directory = Path(temporary)
        source = directory / "collection.csv"
        source.write_bytes(collection)
        source.chmod(0o600)
        args = [sys.executable, "-m", "ai_deckbuilding_tool", action,
                "--collection", str(source), "--collection-confirmed"]
        if offline:
            args.append("--offline")
        if action == "discover":
            args.extend(["--theme", theme])
        else:
            deck = directory / "deck.txt"
            deck.write_text(decklist, encoding="utf-8")
            deck.chmod(0o600)
            args.extend(["--deck", str(deck)])
        try:
            process = subprocess.run(
                args, cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True,
                timeout=TIMEOUT_SECONDS, check=False,
            )
        except subprocess.TimeoutExpired:
            return blocked(action, "CLI_TIMEOUT", launched=True)
        except OSError:
            return blocked(action, "CLI_UNAVAILABLE")
    if len(process.stdout) > MAX_RESPONSE_BYTES:
        return blocked(action, "CLI_RESPONSE_TOO_LARGE", launched=True)
    try:
        report = json.loads(process.stdout.decode("utf-8"))
    except (UnicodeError, ValueError, RecursionError):
        return blocked(action, "CLI_RESPONSE_NOT_JSON", launched=True)
    if (not isinstance(report, dict) or report.get("action") != action
            or report.get("status") not in VALID_STATUSES[action].get(process.returncode, set())
            or type(report.get("validated")) is not bool
            or (report["validated"] != (action == "validate" and process.returncode == 0))):
        return blocked(action, "CLI_RESULT_CONTRACT_MISMATCH", launched=True)
    if process.returncode == 0:
        gateway = report.get("gateway")
        if (not isinstance(gateway, dict)
                or gateway.get("tool_execution") != "EXECUTED"
                or gateway.get("executed") is not True
                or gateway.get("status") != report["status"]):
            return blocked(action, "GATEWAY_EXECUTION_EVIDENCE_MISSING", launched=True)
    return {"cli_exit_code": process.returncode, **report}
