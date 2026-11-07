#!/usr/bin/env python3
"""Opt-in full AtomicCards acceptance; synthetic ownership only, no bulk outputs."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache-dir', type=Path, required=True)
    parser.add_argument('--offline', action='store_true')
    args = parser.parse_args()
    common = ['--cache-dir', str(args.cache_dir.absolute())]
    if args.offline:
        common.append('--offline')
    results = []
    with tempfile.TemporaryDirectory(prefix='atomic-acceptance-') as directory:
        stage = Path(directory)
        collection = stage / 'synthetic.tsv'
        collection.write_text('QuantityX\tName\tEdition\tFoil\tCard Text\tCard Type\tRarity\n5x\tShock\tSynthetic\t\tSynthetic\tInstant\tC\n')
        deck = stage / 'synthetic-deck.txt'
        cases = [('discover', None, 0, 'CANDIDATES_NOT_VALIDATED', 0),
                 ('valid60', '56 Mountain\n4 Shock\n', 0, 'VALIDATED_WITH_LIMITATIONS', 0),
                 ('invalid59', '55 Mountain\n4 Shock\n', 2, 'BLOCKED_INVALID_DECK', 1),
                 ('fivecopies', '55 Mountain\n5 Shock\n', 2, 'BLOCKED_INVALID_DECK', 1),
                 ('unowned', '56 Mountain\n4 Lightning Bolt\n', 2, 'BLOCKED_INVALID_DECK', 1),
                 ('unknown', '56 Mountain\n4 No Such Synthetic Card\n', 2, 'BLOCKED_INVALID_DECK', 1)]
        for name, candidate, expected_exit, expected_status, child in cases:
            action = 'validate' if candidate else 'discover'
            command = [sys.executable, '-m', 'ai_deckbuilding_tool', action, *common,
                       '--synthetic', '--collection', str(collection)]
            if candidate:
                deck.write_text(candidate)
                command += ['--deck', str(deck)]
            else:
                command += ['--theme', 'damage']
            completed = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=180)
            report = json.loads(completed.stdout)
            gateway = report.get('gateway') or {}
            observed = (completed.returncode, report['status'], gateway.get('child_exit_code'))
            if observed != (expected_exit, expected_status, child):
                raise RuntimeError('FULL_INTEGRATION_CASE_FAILED: ' + name + ' ' + str(observed))
            provenance = gateway.get('oracle_provenance')
            if not provenance or gateway.get('oracle_pin_basis') != 'OFFICIAL_FULL_SNAPSHOT_RECEIPT':
                raise RuntimeError('FULL_ORACLE_PROVENANCE_MISSING')
            runtime = report['runtime']
            archive = Path(runtime['archive_path'])
            actual = hashlib.file_digest(archive.open('rb'), 'sha256').hexdigest()
            if actual != provenance['sha256']:
                raise RuntimeError('FULL_ORACLE_HASH_MISMATCH')
            results.append(dict(case=name, exit_code=completed.returncode, status=report['status'],
                                child_exit_code=child, oracle=provenance,
                                actual_archive_sha256=actual, checks=gateway.get('result', {}).get('checks'),
                                output_sha256=hashlib.sha256(completed.stdout).hexdigest()))
        # Exercise the same full snapshot through the stateful controller API.
        sys.path.insert(0, str(ROOT))
        from tools.agent_workflow import Workflow
        canonical = stage / 'synthetic.csv'
        canonical.write_text('Name,Quantity\nShock,5\n')
        deck.write_text('56 Mountain\n4 Shock\n')
        workflow = Workflow(runtime['archive_path'], runtime['sha256'], canonical,
                            scope='current-run-confirmed', confirmed=True,
                            oracle_receipt=runtime['receipt_path'])
        prepared = workflow.prepare('damage')
        if prepared['stages']['DISCOVERY'] != 'COMPLETE_WITH_EVIDENCE':
            raise RuntimeError('FULL_CONTROLLER_PREPARE_FAILED: ' + str(prepared['reasons']))
        workflow.submit(deck, 'Synthetic structural acceptance only; AI authors the list')
        validated = workflow.validate()
        if validated['stages']['VALIDATION'] != 'COMPLETE_WITH_EVIDENCE':
            raise RuntimeError('FULL_CONTROLLER_VALIDATION_FAILED: ' + str(validated['reasons']))
        workflow.review('Synthetic structural test; no strategic strength claimed')
        finalized = workflow.finalize()
        if finalized['status'] != 'COMPLETE_WITH_EVIDENCE':
            raise RuntimeError('FULL_CONTROLLER_FINALIZE_FAILED')
        deck.write_text('55 Mountain\n4 Shock\n')
        stale = workflow.status()
        if stale['status'] != 'STALE' or stale['certificate'] is not None:
            raise RuntimeError('CHANGED_DECK_NOT_INVALIDATED')
        results.append(dict(case='controller-confirmed-synthetic-ownership', status=finalized['status'],
                            changed_deck_status=stale['status'], evidence=finalized['evidence']))
    print(json.dumps(dict(status='PASS_WITH_LIMITATIONS', synthetic_ownership=True, cases=results), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
