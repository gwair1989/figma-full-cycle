import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILLS = {"figma-full-cycle", "figma-feature-spec", "import-figma-assets", "device-usage"}


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="skill-install-")
        self.addCleanup(self.temp.cleanup)
        self.target = Path(self.temp.name) / "skills with spaces"

    def run_install(self, *args):
        return subprocess.run(
            ["bash", str(ROOT / "install.sh"), "--target", str(self.target), *args],
            text=True, capture_output=True,
        )

    def installed(self):
        return {entry.name for entry in self.target.iterdir()} if self.target.exists() else set()

    def test_default_installs_all_four_entry_points(self):
        result = self.run_install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.installed(), SKILLS)
        for name in SKILLS:
            self.assertEqual((self.target / name).resolve(), ROOT / "skills" / name)

    def test_each_companion_can_be_installed_alone(self):
        for name in sorted(SKILLS - {"figma-full-cycle"}):
            with self.subTest(name=name):
                result = self.run_install("--skill", name)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.installed(), {name})
                self.assertEqual(self.run_install("--uninstall", "--skill", name).returncode, 0)

    def test_full_cycle_installs_required_companions_without_device_skill(self):
        result = self.run_install("--skill=figma-full-cycle")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.installed(), SKILLS - {"device-usage"})

    def test_repeatable_selection_and_uninstall_do_not_touch_other_skills(self):
        result = self.run_install("--skill", "device-usage", "--skill", "figma-feature-spec")
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.run_install("--uninstall", "--skill=device-usage")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.installed(), {"figma-feature-spec"})

    def test_full_cycle_uninstall_does_not_remove_its_shared_companions(self):
        self.assertEqual(self.run_install().returncode, 0)
        result = self.run_install("--uninstall", "--skill", "figma-full-cycle")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.installed(), SKILLS - {"figma-full-cycle"})

    def test_invalid_selection_fails_before_any_install(self):
        for name in ("unknown", "../device-usage", ""):
            with self.subTest(name=name):
                result = self.run_install("--skill", "figma-feature-spec", "--skill", name)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.target.exists())

    def test_copy_keeps_device_resources_inside_the_installed_skill(self):
        result = self.run_install("--copy", "--skill", "device-usage")
        self.assertEqual(result.returncode, 0, result.stderr)
        skill = self.target / "device-usage"
        self.assertFalse(skill.is_symlink())
        for relative in ("SKILL.md", "LICENSE", "agents/openai.yaml", "references/control.md",
                         "scripts/capture-evidence.mjs", "scripts/capture-evidence.test.mjs"):
            self.assertEqual((skill / relative).read_bytes(),
                             (ROOT / "skills/device-usage" / relative).read_bytes())
        self.assertFalse(any(entry.is_symlink() for entry in skill.rglob("*")))


if __name__ == "__main__":
    unittest.main()
