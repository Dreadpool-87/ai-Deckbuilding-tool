"""Optional AI-led Casual workflow. Local evidence is not authenticated ownership."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
GATEWAY = ROOT / 'tools/agent_gateway.py'
GATEWAY_PIN = '6422dfcb65c91e2a6197421515005b3b2f42805ead5f840218c12ae571be4534'
STAGES = ('PREFLIGHT', 'SOURCES', 'COLLECTION', 'DISCOVERY', 'CANDIDATE',
          'VALIDATION', 'REVIEW', 'COMPLETE')
LIMITATIONS = [
    'Local report checksums are not authentication against same-user tampering.',
    'Collection confirmation is a caller declaration, not authenticated consent or ownership.',
    'Completion proves a bounded structural workflow, not strategy, full legality or gameplay.',
    'Review and goal are authored assertions, not independently verified strategic reasoning.',
]


def digest(content):
    return hashlib.sha256(content).hexdigest()


class Workflow:
    """One in-memory run. Restarted configuration must earn all evidence again."""

    def __init__(self, oracle, oracle_sha256, collection, scope='synthetic', confirmed=False):
        if (scope not in ('synthetic', 'current-run-confirmed')
                or type(confirmed) is not bool
                or not isinstance(oracle_sha256, str)
                or not re.fullmatch('[0-9a-f]{64}', oracle_sha256)
                or any(not str(p) or len(str(p)) > 4096 for p in (oracle, collection))):
            raise ValueError('INVALID_CONFIGURATION')
        self.configuration = dict(oracle=str(Path(oracle).absolute()),
                                  oracle_sha256=oracle_sha256,
                                  collection=str(Path(collection).absolute()),
                                  scope=scope, confirmed=confirmed)
        self.run_id = str(uuid.uuid4())
        self.stages = dict.fromkeys(STAGES, 'NOT_STARTED')
        self.evidence = {}
        self.reasons = []
        self.certificate = None
        self.snapshot = {}
        self.deck = None
        self.theme = None
        self._candidates = []
        self.goal_hash = None
        self.review_hash = None
        self.support = {}
        # Execute only captured, pinned support code. Reuse Gateway's bounded I/O.
        try:
            if GATEWAY.stat().st_size > 4 * 1024 * 1024:
                raise ValueError()
            code = GATEWAY.read_bytes()
            if digest(code) != GATEWAY_PIN:
                raise ValueError()
            self.support = dict(__file__=str(GATEWAY), __name__='workflow_gateway_support')
            exec(compile(code, str(GATEWAY), 'exec'), self.support)
        except (OSError, ValueError):
            self.reasons = ['GATEWAY_SOURCE_UNVERIFIED']

    def _hashes(self):
        g = self.support
        if not g:
            raise ValueError('GATEWAY_SOURCE_UNVERIFIED')
        paths = {'controller': Path(__file__).resolve(), 'gateway': GATEWAY, 'card_search': ROOT / 'tools/card_search.py',
                 'card_identity': ROOT / 'tools/card_identity.py',
                 'validator': ROOT / 'validator/MTG_Deck_Validator_v1.1.1.py',
                 'oracle': Path(self.configuration['oracle']),
                 'collection': Path(self.configuration['collection'])}
        if self.deck is not None:
            paths['deck'] = self.deck
        return {key: g['_sha'](g['_file'](path, g['MAX_DATA'] if key == 'oracle'
                                        else g['MAX_SMALL'])) for key, path in paths.items()}

    def _fresh(self):
        if not self.snapshot:
            return True
        try:
            observed = self._hashes()
            fresh = self.snapshot == observed
            deck_only = (not fresh and
                         {k: v for k, v in self.snapshot.items() if k != 'deck'} ==
                         {k: v for k, v in observed.items() if k != 'deck'})
        except (OSError, ValueError, self.support['GatewayError']):
            fresh, deck_only = False, False
        if not fresh:
            affected = STAGES[4:] if deck_only else STAGES
            for stage in affected:
                self.stages[stage] = 'STALE'
            self.evidence.pop('validate', None)
            if not deck_only:
                self.evidence = {}
            else:
                self.snapshot.pop('deck', None)
                self.deck = None
            self.certificate = None
            self.review_hash = None
            self.reasons = ['CANDIDATE_CHANGED' if deck_only else 'INPUT_OR_SOURCE_CHANGED']
        return fresh

    def _block(self, reason, stage=None, status='BLOCKED'):
        self.reasons = [reason]
        self.certificate = None
        self.stages['COMPLETE'] = 'NOT_STARTED'
        if stage:
            self.stages[stage] = status
            for later in STAGES[STAGES.index(stage) + 1:]:
                self.stages[later] = 'NOT_STARTED'
            if STAGES.index(stage) < STAGES.index('DISCOVERY'):
                self.evidence.pop('discover', None)
            if STAGES.index(stage) < STAGES.index('VALIDATION'):
                self.evidence.pop('validate', None)
        return self.status(status)

    def status(self, status=None):
        self._fresh()
        missing = [s for s in STAGES if self.stages[s] != 'COMPLETE_WITH_EVIDENCE']
        next_stage = missing[0] if missing else 'COMPLETE'
        actions = dict.fromkeys(STAGES[:4], 'prepare')
        actions.update(CANDIDATE='submit', VALIDATION='validate', REVIEW='review', COMPLETE='finalize')
        if status is None:
            status = ('BLOCKED' if 'BLOCKED' in self.stages.values() else
                      'UNVERIFIED' if 'UNVERIFIED' in self.stages.values() else 'READY')
        current = ('STALE' if 'STALE' in self.stages.values() else
                   'COMPLETE_WITH_EVIDENCE' if self.certificate else status or 'READY')
        # Copies prevent callers from accidentally modifying retained evidence.
        return json.loads(json.dumps(dict(schema_version=1, run_id=self.run_id,
            status=current, stages=self.stages, next_action=actions[next_stage],
            missing_prerequisites=[s for s in missing if s != 'COMPLETE'], reasons=self.reasons, evidence=self.evidence,
            certificate=self.certificate, strategy_verified=False,
            optional={'forge': 'NOT_EXECUTED', 'tester': 'NOT_EXECUTED'},
            limitations=LIMITATIONS)))

    def _invoke(self, action):
        g = self.support
        self.evidence.pop(action, None)
        configuration = self.configuration
        expected_code = {'tools/agent_gateway.py': GATEWAY_PIN,
                         'tools/card_search.py': g['CARD_SEARCH_PIN'],
                         'tools/card_identity.py': g['IDENTITY_PIN'],
                         'validator/MTG_Deck_Validator_v1.1.1.py': g['VALIDATOR_PIN']}
        try:
            with tempfile.TemporaryDirectory(prefix='mtg-workflow-') as directory:
                stage = Path(directory)
                for relative, pin in expected_code.items():
                    content = g['_read_small_file'](ROOT / relative, g['MAX_SMALL'])
                    if digest(content) != pin:
                        raise ValueError()
                    target = stage / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(content)
                args = [sys.executable, '-I', '-S', '-B', str(stage / 'tools/agent_gateway.py'), action]
                if action != 'doctor':
                    args += ['--oracle', configuration['oracle'], '--oracle-sha256',
                             configuration['oracle_sha256'], '--collection', configuration['collection'],
                             '--collection-scope', configuration['scope']]
                    if configuration['confirmed']:
                        args += ['--collection-confirmed']
                    if action == 'discover':
                        args += ['--theme', self.theme]
                    else:
                        args += ['--deck', str(self.deck), '--exact-60']
                completed = g['_bounded_process'](args)
                if len(completed.stdout) > g['MAX_STDOUT'] or len(completed.stderr) > g['MAX_STDERR']:
                    raise ValueError()
                report = json.loads(completed.stdout, object_pairs_hook=g['_distinct_json_object'],
                                    parse_constant=g['_reject_json_constant'],
                                    parse_float=g['_finite_json_float'])
                if (not isinstance(report, dict) or not isinstance(report.get('sources'), dict)
                        or not isinstance(report.get('result', {}), dict)
                        or not isinstance(report.get('result', {}).get('collection_coverage', {}), dict)
                        or type(report.get('executed')) is not bool):
                    raise ValueError()
                allowed = {'doctor': {'RUNTIME_COMPONENTS_PRESENT': (0, None, False)},
                           'discover': {'CANDIDATES_NOT_VALIDATED': (0, 0, True)},
                           'validate': {'VALIDATED_WITH_LIMITATIONS': (0, 0, True),
                                        'BLOCKED_INVALID_DECK': (2, 1, True),
                                        'UNVERIFIED': (3, 3, True)}}
                observed = (completed.returncode, report.get('child_exit_code'), report.get('executed'))
                if (report.get('schema_version') != 1 or report.get('action') != action
                        or observed != allowed[action].get(report.get('status'))
                        or report.get('tool_execution') != ('NOT_EXECUTED' if action == 'doctor' else 'EXECUTED')):
                    raise ValueError()
                sources = report['sources']
                if sources.get('validator_sha256') != (None if action == 'discover' else g['VALIDATOR_PIN']):
                    raise ValueError()
                if action != 'doctor':
                    for key in ('oracle', 'collection') + (('deck',) if action == 'validate' else ()):
                        if sources.get(key + '_sha256') != self.snapshot[key]:
                            raise ValueError()
                    if sources.get('collection_scope') != configuration['scope']:
                        raise ValueError()
                child = report.get('result', {})
                if action == 'discover':
                    if (not isinstance(child.get('results'), list)
                            or not all(isinstance(row, dict) for row in child['results'])):
                        raise ValueError()
                    self._candidates = [
                        {key: row.get(key) for key in
                         ('name', 'owned_copies', 'mana_value', 'color_identity', 'types', 'roles')}
                        for row in child.get('results', [])[:50]]
                if action == 'validate':
                    expected_child = {'VALIDATED_WITH_LIMITATIONS': 'PASS_WITH_LIMITATIONS',
                                      'BLOCKED_INVALID_DECK': 'FAIL', 'UNVERIFIED': 'UNVERIFIED'}
                    if (child.get('status') != expected_child[report['status']]
                            or not isinstance(child.get('checks'), dict)):
                        raise ValueError()
                    if report['status'] == 'VALIDATED_WITH_LIMITATIONS':
                        required = ('deck_parsing', 'deck_size', 'oracle_lookup', 'ownership',
                                    'copy_limit', 'card_types', 'mana_curve')
                        if any(child['checks'].get(key) != 'PASS' for key in required):
                            raise ValueError()
                coverage = child.get('collection_coverage', {})
                receipt = dict(status=report['status'], gateway_exit_code=completed.returncode,
                               child_exit_code=report['child_exit_code'],
                               tool_execution=report['tool_execution'], sources=sources,
                               output_sha256=digest(completed.stdout),
                               checks=child.get('checks', {}),
                               collection_identity_status=coverage.get('identity_status'),
                               unresolved_name_count=coverage.get('unresolved_name_count', 0))
                self.evidence[action] = receipt
                if not self._fresh():
                    return False
                if action == 'discover' and not child.get('results'):
                    self.reasons = ['DISCOVERY_HAS_NO_CANDIDATES']
                    return False
                return report['status'] in ('RUNTIME_COMPONENTS_PRESENT', 'CANDIDATES_NOT_VALIDATED',
                                             'VALIDATED_WITH_LIMITATIONS')
        except (OSError, ValueError, TypeError, KeyError, RecursionError, g['GatewayError']):
            self.reasons = ['GATEWAY_EVIDENCE_UNVERIFIED']
            return False

    def prepare(self, theme):
        self.stages = dict.fromkeys(STAGES, 'NOT_STARTED')
        self.snapshot = {}
        self.evidence = {}
        self.certificate = None
        self.review_hash = None
        self.deck = None
        self.reasons = []
        if not isinstance(theme, str) or not theme.strip() or len(theme.encode()) > 256:
            return self._block('INVALID_THEME')
        self.theme = theme
        if not self.support:
            return self._block('GATEWAY_SOURCE_UNVERIFIED', 'PREFLIGHT', 'UNVERIFIED')
        c = self.configuration
        if (c['scope'] == 'synthetic' and c['confirmed']
                or c['scope'] == 'current-run-confirmed' and not c['confirmed']):
            return self._block('COLLECTION_DECLARATION_REQUIRED_OR_CONTRADICTORY', 'COLLECTION')
        try:
            self.snapshot = self._hashes()
            if self.snapshot['oracle'] != c['oracle_sha256']:
                return self._block('ORACLE_SHA256_MISMATCH', 'SOURCES', 'UNVERIFIED')
            if c['scope'] == 'current-run-confirmed' and c['oracle_sha256'] != self.support['ORACLE_PIN']:
                return self._block('ACTIVE_ORACLE_PIN_UNSUPPORTED', 'SOURCES', 'UNVERIFIED')
        except (OSError, ValueError, self.support['GatewayError']):
            return self._block('INPUT_OR_SOURCE_UNAVAILABLE', 'SOURCES', 'UNVERIFIED')
        if not self._invoke('doctor'):
            return self._block('PREFLIGHT_UNVERIFIED', 'PREFLIGHT', 'UNVERIFIED')
        for stage in STAGES[:3]:
            self.stages[stage] = 'COMPLETE_WITH_EVIDENCE'
        return self.discover(theme)

    def discover(self, theme):
        if not self._fresh():
            return self.status()
        if self.stages['COLLECTION'] != 'COMPLETE_WITH_EVIDENCE':
            return self._block('PREPARE_REQUIRED')
        if not isinstance(theme, str) or not theme.strip() or len(theme.encode()) > 256:
            return self._block('INVALID_THEME')
        self.theme = theme
        self.review_hash = None
        self.certificate = None
        self.evidence.pop('validate', None)
        for stage in STAGES[4:]:
            self.stages[stage] = 'NOT_STARTED'
        if not self._invoke('discover'):
            return self._block(self.reasons[0] if self.reasons else 'DISCOVERY_BLOCKED', 'DISCOVERY', 'UNVERIFIED')
        self.stages['DISCOVERY'] = 'COMPLETE_WITH_EVIDENCE'
        self.reasons = []
        # Candidate names are local discovery output, never certificate contents.
        return dict(self.status(), candidates=self._candidates)

    def submit(self, deck, goal):
        self._fresh()
        if self.stages['DISCOVERY'] != 'COMPLETE_WITH_EVIDENCE':
            return self._block('DISCOVERY_REQUIRED')
        if not isinstance(goal, str) or not goal.strip() or len(goal.encode()) > 4096:
            return self._block('INVALID_GOAL')
        self.certificate = None
        self.review_hash = None
        for stage in STAGES[4:]:
            self.stages[stage] = 'NOT_STARTED'
        self.evidence.pop('validate', None)
        try:
            self.deck = self.support['_file'](Path(deck).absolute(), self.support['MAX_SMALL'])
            observed = self._hashes()
            if {k: v for k, v in observed.items() if k != 'deck'} != {
                    k: v for k, v in self.snapshot.items() if k != 'deck'}:
                self.deck = None
                self._fresh()
                return self.status()
            self.snapshot = observed
        except (OSError, ValueError, self.support['GatewayError']):
            self.deck = None
            return self._block('CANDIDATE_UNAVAILABLE', 'CANDIDATE')
        self.goal_hash = digest(goal.encode())
        self.stages['CANDIDATE'] = 'COMPLETE_WITH_EVIDENCE'
        self.reasons = []
        return self.status()

    def validate(self):
        if not self._fresh():
            return self.status()
        self.certificate = None
        self.review_hash = None
        self.stages['REVIEW'] = self.stages['COMPLETE'] = 'NOT_STARTED'
        if self.stages['CANDIDATE'] != 'COMPLETE_WITH_EVIDENCE':
            return self._block('CANDIDATE_REQUIRED')
        if not self._invoke('validate'):
            return self._block('VALIDATION_NOT_APPROVED', 'VALIDATION', 'UNVERIFIED')
        self.stages['VALIDATION'] = 'COMPLETE_WITH_EVIDENCE'
        self.reasons = []
        return self.status()

    def review(self, note):
        if not self._fresh():
            return self.status()
        if self.stages['VALIDATION'] != 'COMPLETE_WITH_EVIDENCE':
            return self._block('VALIDATION_REQUIRED')
        if not isinstance(note, str) or not note.strip() or len(note.encode()) > 8192:
            return self._block('INVALID_REVIEW')
        self.review_hash = digest(note.encode())
        self.certificate = None
        self.stages['COMPLETE'] = 'NOT_STARTED'
        self.stages['REVIEW'] = 'COMPLETE_WITH_EVIDENCE'
        self.reasons = []
        return self.status()

    def finalize(self):
        if not self._fresh():
            return self.status()
        if any(self.stages[s] != 'COMPLETE_WITH_EVIDENCE' for s in STAGES[:-1]):
            return self._block('MISSING_PREREQUISITES')
        # Replay executable requirements, never certify imported receipts.
        for action, stage in (('doctor', 'PREFLIGHT'), ('discover', 'DISCOVERY'), ('validate', 'VALIDATION')):
            if not self._invoke(action):
                return self._block('FINAL_EVIDENCE_UNVERIFIED', stage, 'UNVERIFIED')
        self.stages['COMPLETE'] = 'COMPLETE_WITH_EVIDENCE'
        self.certificate = dict(run_id=self.run_id, deck_sha256=self.snapshot['deck'],
                                sources=dict(self.snapshot), validator_profile='github-main-v0.2',
                                goal_sha256=self.goal_hash, review_sha256=self.review_hash,
                                strategy_verified=False,
                                execution={k: v['output_sha256'] for k, v in self.evidence.items()})
        self.certificate['checksum_sha256'] = digest(
            json.dumps(self.certificate, sort_keys=True, separators=(',', ':')).encode())
        self.reasons = []
        return self.status()

    def checkpoint(self, path):
        """Write local private configuration only; never serialize trusted evidence."""
        payload = json.dumps(dict(schema_version=1, configuration=self.configuration)).encode()
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'wb') as handle:
                handle.write(payload)
        except OSError:
            raise ValueError('CHECKPOINT_UNAVAILABLE') from None

    @classmethod
    def resume(cls, path, *, confirmed=False):
        try:
            if Path(path).is_symlink():
                raise ValueError()
            descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0)
                                 | getattr(os, 'O_NOFOLLOW', 0))
            with os.fdopen(descriptor, 'rb') as handle:
                if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                    raise ValueError()
                content = handle.read(16385)
            if len(content) > 16384:
                raise ValueError()
            data = json.loads(content)
            if set(data) != {'schema_version', 'configuration'} or data['schema_version'] != 1:
                raise ValueError()
            configuration = dict(data['configuration'])
            configuration['confirmed'] = confirmed
            return cls(**configuration)
        except (OSError, ValueError, TypeError, KeyError, RecursionError):
            raise ValueError('UNTRUSTED_CHECKPOINT') from None
