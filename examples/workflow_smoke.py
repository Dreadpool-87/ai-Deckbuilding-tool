"""Synthetic API demonstration with a fixed AI-authored fixture, no card selection."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.agent_workflow import Workflow


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skip-discovery', action='store_true')
    parser.add_argument('--skip-validation', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        oracle, pool, deck = (folder / name for name in ('oracle.json', 'pool.csv', 'deck.txt'))
        oracle.write_text(json.dumps({'data': {
            'Island': [{'name': 'Island', 'types': ['Land'], 'supertypes': ['Basic'],
                        'colorIdentity': ['U'], 'manaValue': 0}],
            'Fixture Insight': [{'name': 'Fixture Insight', 'types': ['Instant'],
                                 'colorIdentity': ['U'], 'manaValue': 1, 'manaCost': '{U}',
                                 'text': 'Draw a card.'}]}}))
        pool.write_text('Name,Quantity\nFixture Insight,4\n')
        # Authored test input, deliberately extreme to isolate structural gates.
        deck.write_text('56 Island\n4 Fixture Insight\n')
        run = Workflow(oracle, hashlib.sha256(oracle.read_bytes()).hexdigest(), pool)
        if not args.skip_discovery:
            run.prepare('draw')
        run.submit(deck, 'Synthetic 60-card structural demonstration')
        if not args.skip_validation:
            run.validate()
        run.review('The selected fixture isolates counts. Its 56 lands lack strategic balance.')
        report = run.finalize()
        print(json.dumps(report, indent=2))
        return 0 if report['status'] == 'COMPLETE_WITH_EVIDENCE' else 2


if __name__ == '__main__':
    raise SystemExit(main())
