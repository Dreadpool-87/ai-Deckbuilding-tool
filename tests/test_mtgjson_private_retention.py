"""Offline checks for fail-closed two-snapshot MTGJSON retention."""
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "plan_mtgjson_private_retention.py"
spec = importlib.util.spec_from_file_location("mtgjson_retention", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def release(n, tag=None, draft=True, assets=None):
    return {
        "id": n,
        "tag_name": tag or f"mtgjson-private-bundle-5.3.{n}",
        "draft": draft,
        "assets": assets if assets is not None else [
            {"id": n * 100 + i + 1, "name": name, "size": 100}
            for i, name in enumerate(sorted(mod.REQUIRED))
        ],
    }


class TestRetentionPlanner(unittest.TestCase):
    def test_keep_one(self):
        p = mod.choose([release(1)], release(1)["tag_name"])
        self.assertEqual(p["older"], [])

    def test_keep_two(self):
        rows = [release(1), release(2)]
        p = mod.choose(rows, rows[1]["tag_name"])
        self.assertEqual(len(p["keep"]), 2)
        self.assertEqual(p["older"], [])

    def test_three_prunes_only_oldest(self):
        rows = [release(1), release(2), release(3)]
        p = mod.choose(rows, rows[-1]["tag_name"])
        self.assertEqual([x["id"] for x in p["older"]], [1])
        self.assertEqual([x["id"] for x in p["keep"]], [3, 2])

    def test_historical_atomic_release_never_managed(self):
        rows = [release(1), release(2), release(3),
                release(100, "mtgjson-atomic-5.3.0+20261013", draft=False)]
        p = mod.choose(rows, rows[2]["tag_name"])
        self.assertEqual([x["id"] for x in p["older"]], [1])
        self.assertEqual(p["total_managed"], 3)

    def test_unrelated_release_never_managed(self):
        rows = [release(1), release(2), release(3),
                release(900, "casual-private-alpha-v0.1.0", draft=False)]
        p = mod.choose(rows, rows[2]["tag_name"])
        self.assertEqual([x["id"] for x in p["older"]], [1])

    def test_missing_asset_blocks_everything(self):
        rows = [release(1), release(2), release(3)]
        rows[1]["assets"].pop()
        with self.assertRaises(ValueError):
            mod.choose(rows, rows[-1]["tag_name"])

    def test_extra_asset_blocks_everything(self):
        rows = [release(1), release(2), release(3)]
        rows[0]["assets"].append({"name": "unrecognised.zip", "id": 99999, "size": 4})
        with self.assertRaises(ValueError):
            mod.choose(rows, rows[-1]["tag_name"])

    def test_non_draft_managed_release_blocks_everything(self):
        rows = [release(1, draft=False), release(2), release(3)]
        with self.assertRaises(ValueError):
            mod.choose(rows, rows[-1]["tag_name"])

    def test_invalid_asset_metadata_blocks(self):
        rows = [release(1), release(2), release(3)]
        rows[0]["assets"][0]["size"] = 0
        with self.assertRaises(ValueError):
            mod.choose(rows, rows[-1]["tag_name"])

    def test_duplicate_release_id_blocks(self):
        rows = [release(1), release(1), release(3)]
        with self.assertRaises(ValueError):
            mod.choose(rows, rows[-1]["tag_name"])

    def test_missing_current_release_blocks(self):
        with self.assertRaises(ValueError):
            mod.choose([release(1), release(2)], "mtgjson-private-bundle-no-such-version")

    def test_old_tag_cannot_run_cleanup(self):
        rows = [release(1), release(2), release(3)]
        with self.assertRaises(ValueError):
            mod.choose(rows, rows[0]["tag_name"])

    def test_invalid_tag_blocks(self):
        with self.assertRaises(ValueError):
            mod.choose([release(1)], "../delete_everything")

    def test_no_releases_blocks(self):
        with self.assertRaises(ValueError):
            mod.choose([], "mtgjson-private-bundle-5.3.1")


if __name__ == "__main__":
    unittest.main()
