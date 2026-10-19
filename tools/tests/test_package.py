import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class PackageTests(unittest.TestCase):
    def test_portable_and_codex_manifests_describe_the_same_package(self):
        portable = json.loads((ROOT / "plugin.json").read_text())
        codex = json.loads((ROOT / ".codex-plugin/plugin.json").read_text())
        for key in ("name", "version", "description"):
            self.assertEqual(portable[key], codex[key])
        self.assertEqual(codex["skills"], "./skills/")
        self.assertTrue((ROOT / codex["skills"]).is_dir())

    def test_marketplace_resolves_the_bundle_inside_a_fresh_checkout(self):
        marketplace = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text())
        self.assertEqual(len(marketplace["plugins"]), 1)
        entry = marketplace["plugins"][0]
        self.assertEqual(entry["source"]["source"], "local")
        self.assertTrue(entry["source"]["path"].startswith("./"))
        plugin_root = (ROOT / entry["source"]["path"]).resolve()
        self.assertEqual(plugin_root, ROOT)
        manifest = json.loads((plugin_root / "plugin.json").read_text())
        self.assertEqual(entry["name"], manifest["name"])
        self.assertEqual(entry["policy"]["installation"], "AVAILABLE")

    def test_all_four_skill_entry_points_are_real_bundled_directories(self):
        expected = {"figma-full-cycle", "figma-feature-spec", "import-figma-assets", "device-usage"}
        actual = {entry.parent.name for entry in (ROOT / "skills").glob("*/SKILL.md")}
        self.assertEqual(actual, expected)
        for name in expected:
            directory = ROOT / "skills" / name
            self.assertFalse(directory.is_symlink(), name)
            self.assertFalse(any(entry.is_symlink() for entry in directory.rglob("*")), name)


if __name__ == "__main__":
    unittest.main()
