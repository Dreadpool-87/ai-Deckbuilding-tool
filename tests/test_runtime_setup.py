"""Offline runtime acceptance with generated synthetic full-shaped metadata."""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]

class RuntimeTests(unittest.TestCase):
    def module(self):
        path = ROOT / 'tools/atomic_runtime.py'
        self.assertTrue(path.is_file(), 'Official AtomicCards runtime is missing')
        spec = importlib.util.spec_from_file_location('atomic_runtime_test', path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_verified_cache_and_corruption(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cards = {f'Card {i}': [{'name': f'Card {i}', 'types': ['Instant'], 'manaValue': 1}] for i in range(20001)}
            raw = gzip.compress(json.dumps({'meta': {'version': 'synthetic'}, 'data': cards}).encode())
            sha = hashlib.sha256(raw).hexdigest()
            def fetch(name, limit=131072):
                return b'{"data":{"version":"synthetic"}}' if name == 'Meta.json' else sha.encode()
            def download(path):
                path.write_bytes(raw)
            with mock.patch.object(m, 'fetch', side_effect=fetch), mock.patch.object(m, 'download', side_effect=download):
                receipt = m.setup(root)
                self.assertEqual(receipt['sha256'], sha)
                self.assertEqual(m.setup(root)['cache_status'], 'REUSED_VERIFIED')
            self.assertEqual(m.setup(root, offline=True)['sha256'], sha)
            (root / (sha + '.json.gz')).write_bytes(b'corrupt')
            with self.assertRaises(ValueError):
                m.setup(root, offline=True)

    def test_missing_offline_cache_fails(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                m.setup(Path(directory), offline=True)

    def test_normalizer_tsv_and_ambiguous_quantity(self):
        from ai_deckbuilding_tool import collection_import as m
        raw = b'Card Name\tRegular\tFoil\nShock\t2\t1\n'
        result, evidence = m.normalize(raw)
        self.assertEqual(result, b'Name,Quantity\nShock,3\n')
        self.assertEqual(evidence['original_sha256'], hashlib.sha256(raw).hexdigest())
        for raw in (b'Name,Quantity,Count\nShock,2,3\n', b'Name,Quantity\nShock,1.5\n'):
            with self.assertRaises(ValueError):
                m.normalize(raw)

class NewCliContractTests(unittest.TestCase):
    def test_setup_is_a_machine_readable_command(self):
        import subprocess, sys
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, '-m', 'ai_deckbuilding_tool', 'setup',
                                     '--offline', '--cache-dir', directory], cwd=ROOT,
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, 3)
        self.assertEqual(json.loads(result.stdout)['reason_codes'], ['NO_VERIFIED_OFFLINE_CACHE'])

class CollectionExportTests(unittest.TestCase):
    def test_quantity_x_and_foil_marker_are_not_two_owned_counts(self):
        from ai_deckbuilding_tool.collection_import import normalize
        raw = b'QuantityX\tName\tEdition\tFoil\tCard Text\n5x\tFixture Drake\tFixture Set\t\t"Flying"\n'
        value, evidence = normalize(raw)
        self.assertEqual(value, b'Name,Quantity\nFixture Drake,5\n')

class ExportTextTests(unittest.TestCase):
    def test_unescaped_quotes_in_nonownership_tsv_text(self):
        from ai_deckbuilding_tool.collection_import import normalize
        raw = b'QuantityX\tName\tEdition\tFoil\tCard Text\tCard Type\tRarity\n2x\tFixture Aura\tTest\t\t"Enchanted creature has "Flying"."\tEnchantment\tC\n'
        result, _ = normalize(raw)
        self.assertEqual(result, b'Name,Quantity\nFixture Aura,2\n')

class RuntimeFailureTests(RuntimeTests):
    def test_failure_does_not_publish_partial_or_replace_current(self):
        m = self.module()
        for failure in (OSError('network'), InterruptedError('interrupted')):
            with self.subTest(failure=type(failure).__name__), tempfile.TemporaryDirectory() as directory:
                cache = Path(directory)
                with mock.patch.object(m, 'upstream', return_value=('5.3.0', 'a'*64)), mock.patch.object(m, 'download', side_effect=failure):
                    with self.assertRaises(OSError):
                        m.setup(cache)
                self.assertFalse((cache/'current.json').exists())
                self.assertEqual(list(cache.iterdir()), [])

    def test_upstream_change_during_verification_fails_closed(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            with mock.patch.object(m, 'upstream', side_effect=[('v1','a'*64),('v2','b'*64)]), mock.patch.object(m, 'download', side_effect=lambda p:p.write_bytes(b'data')), mock.patch.object(m, 'inspect_archive', return_value={'card_names':20001}):
                with self.assertRaisesRegex(ValueError, 'UPSTREAM_CHANGED'):
                    m.setup(cache)
            self.assertFalse((cache/'current.json').exists())

    def test_wrong_digest_rejected(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'bad.gz';p.write_bytes(b'not an archive')
            with self.assertRaisesRegex(ValueError, 'SHA256_MISMATCH'):
                m.inspect_archive(p, 'a'*64, 'v1')

    def test_symlink_cache_does_not_touch_target(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);target=root/'target';target.mkdir();link=root/'link';link.symlink_to(target)
            with self.assertRaisesRegex(ValueError, 'SYMLINK'):
                m.setup(link, offline=True)
            self.assertEqual(list(target.iterdir()), [])
