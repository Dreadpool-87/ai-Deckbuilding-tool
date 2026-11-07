#!/usr/bin/env python3
"""Validate GitHub Actions YAML syntax and core workflow structure.

Requires PyYAML during CI, not as a runtime dependency of the deck validator.
This is not a replacement for actionlint or live workflow execution.
"""
import hashlib
from pathlib import Path
import re
import subprocess
import sys

try:
    import yaml
except ImportError:
    raise SystemExit("PyYAML is needed only for the workflow-syntax CI job")


def main():
    root = Path(__file__).resolve().parents[1]
    workflows = sorted(path for path in (root / ".github/workflows").iterdir()
                       if path.suffix in {".yml", ".yaml"})
    if len(workflows) < 5:
        raise ValueError("Expected at least five workflow files")
    for path in workflows:
        with path.open(encoding="utf-8") as f:
            data = yaml.load(f, Loader=yaml.BaseLoader)
        if not isinstance(data, dict) or "name" not in data or "on" not in data:
            raise ValueError(f"Missing workflow name/trigger: {path}")
        if not isinstance(data.get("jobs"), dict) or not data["jobs"]:
            raise ValueError(f"Missing jobs: {path}")
        if data.get("permissions") != {"contents": "read"}:
            raise ValueError(f"Expected read-only workflow permissions: {path}")
        for job_name, job in data["jobs"].items():
            if not isinstance(job, dict) or not isinstance(job.get("steps"), list):
                raise ValueError(f"Invalid steps in {path}: {job_name}")
            job_permissions = job.get("permissions", data["permissions"])
            private_bundle_job = (
                path.name == "mtgjson-private-draft-bundle.yml"
                and job_name == "private-draft-snapshot"
                and job.get("if") == "github.event.repository.private == true"
            )
            atomic_pointer_job = (
                path.name == "mtgjson-atomic-update.yml"
                and job_name == "update-pointer"
                and job.get("if") == "github.ref == 'refs/heads/main'"
            )
            expected_permissions = (
                {"contents": "write", "pull-requests": "write"} if atomic_pointer_job
                else {"contents": "write"} if private_bundle_job
                else {"contents": "read"}
            )
            if job_permissions != expected_permissions:
                raise ValueError(f"Unexpected job permissions in {path}: {job_name}")
            for step in job["steps"]:
                if not isinstance(step, dict) or ("run" not in step and "uses" not in step):
                    raise ValueError(f"Invalid workflow step in {path}: {job_name}")
                if "uses" in step:
                    action = step["uses"]
                    if not re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", action):
                        raise ValueError(f"Unpinned action in {path}: {action}")
                    if action.startswith("actions/checkout@"):
                        if step.get("with", {}).get("persist-credentials") != "false":
                            raise ValueError(f"Checkout must disable persisted credentials: {path}")
                if "run" in step:
                    shell_code = step["run"]
                    if "${{" in shell_code:
                        raise ValueError(f"Pass Actions expressions through env instead of shell code: {path}")
                    # All run steps in these Linux workflows use bash-compatible syntax.
                    checked = subprocess.run(["bash", "-n"], input=shell_code,
                                             text=True, capture_output=True, check=False)
                    if checked.returncode:
                        raise ValueError(f"Bash syntax error in {path}: {job_name}; " +
                                         checked.stderr.strip()[:250])
        print(f"YAML parse OK: {path.relative_to(root)}")
        if path.name == "forge-custom.yml":
            inputs = data["on"]["workflow_dispatch"]["inputs"]
            for label in ("a", "b"):
                relative_path = inputs[f"deck_{label}"]["default"]
                default_deck = (root / relative_path).resolve(strict=True)
                if not default_deck.is_relative_to(root):
                    raise ValueError(f"Forge default deck must stay inside the repository: {relative_path}")
                expected = inputs[f"sha_{label}"]["default"]
                if hashlib.sha256(default_deck.read_bytes()).hexdigest() != expected:
                    raise ValueError(f"Stale Forge default deck SHA-256: {relative_path}")
    for filename in ("forge-runtime-download.yml", "forge-smoke.yml",
                     "mtgjson-atomic-update.yml"):
        path = root / ".github/workflows" / filename
        raw = path.read_text(encoding="utf-8")
        if "gh release create" in raw or "gh release download" in raw or "actions/upload-artifact" in raw and filename != "forge-smoke.yml":
            raise ValueError(f"Workflow appears to re-host an upstream archive: {path}")
    # The only public MTGJSON write privilege is a reviewed metadata-only PR.
    atomic = (root / ".github/workflows/mtgjson-atomic-update.yml").read_text(encoding="utf-8")
    for required in ('17 7 * * 0', 'scripts/record_mtgjson_atomic_pointer.py',
                     'data/mtgjson_atomic_latest.json', 'gh pr create',
                     'pull-requests: write'):
        if required not in atomic:
            raise ValueError("Missing reviewed weekly MTGJSON pointer mechanism: " + required)
    for forbidden in ('gh release upload', 'gh release create', 'actions/upload-artifact',
                      'git push origin main'):
        if forbidden in atomic:
            raise ValueError("Weekly MTGJSON verification must not distribute archives or push main")

    private = root / ".github/workflows/mtgjson-private-draft-bundle.yml"
    if private.exists():
        proposed = yaml.load(private.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        jobs = proposed.get("jobs", {})
        if len(jobs) != 1 or next(iter(jobs.values())).get("permissions", {}).get("contents") != "write":
            raise ValueError("Private draft workflow requires tightly scoped job write permission")
        source = private.read_text(encoding="utf-8")
        for safeguard in ("--draft", "'.private'", "gh release create",
                          "manifest.json", "MTGJSON-MIT.txt", "THIRD_PARTY_NOTICES.md"):
            if safeguard not in source:
                raise ValueError("Missing private draft guardrail: " + safeguard)
        for forbidden in ("gh release edit", "gh release upload", "--latest"):
            if forbidden in source:
                raise ValueError("Private drafts must never be promoted or overwritten automatically")
    print("All workflow syntax, read-only upstream and private DRAFT policy checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
