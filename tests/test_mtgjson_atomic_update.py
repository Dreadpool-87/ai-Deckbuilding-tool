"""Offline tests for MTGJSON update safety checks."""
import importlib.util
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "update_mtgjson_atomic.py"
spec = importlib.util.spec_from_file_location("update_mtgjson_atomic", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def card(name):
    return {"name": name, "types": ["Creature"], "manaValue": 1}

class TestAtomicUpdater(unittest.TestCase):
    def test_checksum_plain(self):
        self.assertEqual(mod.parse_checksum(("a"*64).encode()), "a"*64)

    def test_checksum_with_filename(self):
        self.assertEqual(mod.parse_checksum((("B"*64) + "  AtomicCards.json.gz").encode()), "b"*64)

    def test_reject_malformed_checksum(self):
        with self.assertRaises(ValueError):
            mod.parse_checksum(b"not a sha256")

    def test_reject_bad_root(self):
        with self.assertRaises(ValueError):
            mod.validate_data({"data": []}, "5.3")

    def test_reject_insufficient_card_coverage(self):
        with self.assertRaises(ValueError):
            mod.validate_data({"data": {"Shock": [card("Shock")]}, "meta": {"version": "5.3"}}, "5.3")

    def test_reject_mismatched_version(self):
        data = {f"Card {i}": [card(f"Card {i}")] for i in range(20001)}
        data.update({name: [card(name)] for name in ("Mountain", "Shock", "Chandra's Spitfire")})
        with self.assertRaises(ValueError):
            mod.validate_data({"data": data, "meta": {"version": "5.2"}}, "5.3")

if __name__ == "__main__":
    unittest.main()
