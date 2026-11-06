#!/usr/bin/env python3
"""One real Forge AI-vs-AI smoke game with raw logs and strict outcome checks.

Never claim a win/draw from exit code alone. Forge may print a Draw after exceptions.
"""
import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
import zipfile
from pathlib import Path

RESULT_WIN = re.compile(
    r"^Game Result:\s*Game 1 ended in (\d+) ms\.\s+(Ai\([12]\)-.+?) has won!\s*$",
    re.MULTILINE,
)
RESULT_DRAW = re.compile(
    r"^Game Result:\s*Game 1 ended in a Draw!\s*Took (\d+) ms\.\s*$",
    re.MULTILINE,
)
ERROR = re.compile(
    r"(?im)^(?:\s*(?:Caused by: )?(?:Exception in thread|[\w.$]+(?:Exception|Error)(?::|$))|"
    r"Could not load deck|No deck found|Stopping slow match as draw)"
)


def locate_jar(directory):
    candidates = []
    for jar in directory.rglob("*.jar"):
        try:
            with zipfile.ZipFile(jar) as z:
                manifest = z.read("META-INF/MANIFEST.MF").decode("utf-8", "replace")
            if "Main-Class:" not in manifest:
                continue
            name = jar.name.lower()
            if "installer" in name or "adventure" in name:
                continue
            priority = (0 if "forge-gui-desktop" in name else
                        1 if "forge" in name and "dependencies" in name else
                        2 if "forge" in name else 3)
            candidates.append((priority, len(jar.parts), jar))
        except (zipfile.BadZipFile, KeyError, OSError):
            pass
    if not candidates:
        raise FileNotFoundError("No suitable executable desktop Forge jar with Main-Class found")
    return sorted(candidates)[0][2]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--decks", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=420)
    parser.add_argument("--clock", type=int, default=120)
    parser.add_argument("--seed", type=int, default=20261014)
    args = parser.parse_args()

    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    stdout_path, stderr_path = out / "stdout.log", out / "stderr.log"
    stdout_path.touch()
    stderr_path.touch()
    result = {
        "classification": "NOT_EXECUTED",
        "game_started_verified": False,
        "game_result_verified": False,
        "source_decks": [],
        "requested_games": 1,
        "seed_requested": args.seed,
        "forge_clock_seconds": args.clock,
        "process_timeout_seconds": args.timeout,
    }
    status = 1
    try:
        jar = locate_jar(args.runtime.resolve())
        manifest = json.loads((args.decks.resolve() / "deck-manifest.json").read_text(encoding="utf-8"))
        entries = manifest["decks"]
        result["source_decks"] = [e["source"] for e in entries]
        result["deck_manifest_sha256"] = sha256(args.decks.resolve() / "deck-manifest.json")
        if len(entries) != 2 or any(e["cards"] != 60 or not e["source_to_forge_card_counts_equal"]
                                    for e in entries):
            raise ValueError("Deck input manifest failed 60-card/source-integrity check")
        for entry in entries:
            if sha256(args.decks.resolve() / entry["forge_file"]) != entry["forge_sha256"]:
                raise ValueError("Converted Forge deck checksum mismatch")

        deck_names = [e["forge_file"] for e in entries]
        command = [
            "java", "-Xmx2g", "-Djava.awt.headless=true",
            "-jar", str(jar), "sim",
            "-d", *deck_names,
            "-D", str(args.decks.resolve()), "-n", "1", "-f", "constructed",
            "-s", str(args.seed), "-c", str(args.clock),
        ]
        result.update({"jar": str(jar.relative_to(args.runtime.resolve())),
                       "jar_sha256": sha256(jar),
                       "command": command, "cwd": str(jar.parent)})
        print("Starting real Forge process:", " ".join(command), flush=True)
        start = time.monotonic()
        with stdout_path.open("w", encoding="utf-8", errors="replace") as stdout, \
             stderr_path.open("w", encoding="utf-8", errors="replace") as stderr:
            process = subprocess.Popen(command, cwd=jar.parent, stdout=stdout, stderr=stderr,
                                       start_new_session=True)
            result["process_spawned"] = True
            try:
                result["exit_code"] = process.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                result["exit_code"] = process.returncode
                result["process_timed_out"] = True
        result["wall_time_seconds"] = round(time.monotonic() - start, 3)

        output = stdout_path.read_text(encoding="utf-8", errors="replace")
        errors = stderr_path.read_text(encoding="utf-8", errors="replace")
        result["stdout_bytes"] = stdout_path.stat().st_size
        result["stderr_bytes"] = stderr_path.stat().st_size
        header_ok = ("Simulation mode" in output and
                     re.search(r"-\s+(?:one|1)\s+game of Constructed", output, re.IGNORECASE) is not None)
        imported = all("Ai(" + str(i + 1) + ")-" + e["name"] in output
                       for i, e in enumerate(entries))
        result["game_started_verified"] = bool(header_ok and imported)
        result["deck_load_evidence"] = bool(imported)
        win = list(RESULT_WIN.finditer(output))
        draw = list(RESULT_DRAW.finditer(output))
        result["result_lines_found"] = len(win) + len(draw)
        result["forge_result_lines"] = [m.group(0).strip() for m in win + draw]
        result["forge_header_verified"] = bool(header_ok)
        result["forge_timeout_log_found"] = "Stopping slow match as draw" in output
        result["error_signature_found"] = bool(ERROR.search(output + "\n" + errors))
        card_load_error = re.search(r"(?im)^.*(?:unknown card|card not found|missing card|unsupported card|could not load deck|no deck found).*$", output + "\n" + errors)
        result["card_load_error"] = card_load_error.group(0)[:500] if card_load_error else None
        result["starting_player"] = None  # Not reliably exposed by current Forge CLI parser
        result["turn_count"] = None  # Do not infer turns from result duration
        result["internal_error_examples"] = [line[:300] for line in (output + "\n" + errors).splitlines()
                                            if ERROR.search(line)][:5]

        if result.get("process_timed_out") or result["forge_timeout_log_found"]:
            result["classification"] = "TIMEOUT"
        elif result["card_load_error"]:
            result["classification"] = "BLOCKED"
        elif result["exit_code"] != 0 or (result["error_signature_found"] and
                                          not result["forge_timeout_log_found"]):
            result["classification"] = "CRASH"
        elif not result["game_started_verified"] or len(win) + len(draw) != 1:
            result["classification"] = "INCOMPLETE"
        elif draw:
            result["classification"] = "DRAW"
            result["game_result_verified"] = True
            result["forge_duration_ms"] = int(draw[0].group(1))
        else:
            expected = {f"Ai({i+1})-{e['name']}": label
                        for i, (e, label) in enumerate(zip(entries, ("WIN_A", "WIN_B")))}
            winner = win[0].group(2)
            result["forge_winner"] = winner
            result["forge_duration_ms"] = int(win[0].group(1))
            result["classification"] = expected.get(winner, "INCOMPLETE")
            result["game_result_verified"] = result["classification"] in ("WIN_A", "WIN_B")

        status = 0 if result["game_result_verified"] else 2
    except Exception as exc:
        result["classification"] = "BLOCKED"
        result["setup_error"] = f"{type(exc).__name__}: {exc}"
        print("Forge smoke test setup failed:", result["setup_error"], file=sys.stderr, flush=True)
    finally:
        (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                         encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return status


if __name__ == "__main__":
    sys.exit(main())
