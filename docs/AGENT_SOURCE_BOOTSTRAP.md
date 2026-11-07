# Source access before automatic setup

A failed `git clone` only tests Git access from that shell. It does not establish whether an authorized GitHub connector can retrieve exact file contents. Reading a GitHub page and running local Python are separate capabilities. Do not report a network cause beyond the actual error observed.

## Required recovery order

1. Reuse a verified local checkout when available. Otherwise try the host's permitted repository acquisition route. Record the exact clone error without secrets.
2. If shell GitHub access is unavailable, inspect available authorized GitHub connector capabilities. Resolve `main` once to a full 40-character commit SHA. Use that same commit for **every** source request; never mix moving `main` responses.
3. Fetch `runtime/source_manifest.json` and `scripts/restore_agent_runtime.py` at that commit using the connector's full file-content operation. Preserve exact UTF-8 bytes, not search excerpts, rendered HTML, summaries, escaped text or truncated responses. Verify the bootstrap script's SHA-256 against the manifest **before executing it**. These values are computed by the agent, not by the user.
4. Fetch every file listed in the manifest at the same commit. Write a private transport JSON with exactly `{"commit":"<resolved SHA>","files":{"<relative source path>":"<exact UTF-8 file contents>"}}`. Use JSON serialization, not shell interpolation. No collection, deck or Oracle data belongs in this transport.
5. Save the exact manifest bytes and transport locally. Calculate the manifest SHA-256 from the connector response and run the checked bootstrap script:

```sh
python /private/restore_agent_runtime.py \
  --manifest /private/source_manifest.json \
  --payload /private/source_payload.json \
  --destination /private/agent-runtime \
  --expected-commit <resolved-commit> \
  --expected-manifest-sha256 <connector-manifest-sha256>
cd /private/agent-runtime
python -m ai_deckbuilding_tool setup
python -m ai_deckbuilding_tool discover --collection /private/current.csv --collection-confirmed --theme damage
# AI authors candidate.txt, then performs the actual check:
python -m ai_deckbuilding_tool validate --collection /private/current.csv --collection-confirmed --deck /private/candidate.txt
```

The restorer performs no network or Git operation. It accepts only the fixed source allowlist, verifies all hashes before installing, rejects extra files/symlinks/existing destinations, and installs atomically in a private directory. `SOURCE_RECEIPT.json` records the commit, manifest digest and file hashes. This is a runnable minimal runtime, **not a complete Git checkout**. Optional synergy/Forge/Commander tools are not included; use a full checkout for those. The stable Builder/Tester prompts and controller are included.

Source restoration is not Oracle setup or validation. Record each actual status and exit code separately. For disconnected Oracle setup, use `setup --offline` only with an intact previously verified official cache. Never replace full AtomicCards with a synthetic/slim fixture to claim real validation.

## Honest failure boundary

A connector may return files without exposing exact content or local materialization. If exact bytes cannot be recovered, stop with `ENVIRONMENT_BLOCKED / SOURCE_CONTENT_UNAVAILABLE`, naming the attempted routes and their actual errors. If code is restored but MTGJSON is unavailable, report the separate Oracle/network blocker. Do not promise that every chat host has a connector, local Python or upstream network permission. Do not circumvent host access controls or ask users to calculate hashes/download Oracle data.

The trusted commit and manifest are established by the authorized connector response. A caller-provided label and local hashes alone do not authenticate a malicious transport. Existing hardcoded Gateway/Validator source pins remain mandatory after restoration.

## Manifest maintenance

When any allowlisted source changes, update `runtime/source_manifest.json` SHA-256 values and the repository `SHA256SUMS.txt`. Tests check all manifest entries against maintained files. Never put this manifest's own hash inside itself. The consumer pins the manifest to the selected commit and records its exact byte digest.
