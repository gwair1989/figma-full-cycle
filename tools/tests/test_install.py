import subprocess
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILLS = {"figma-full-cycle", "figma-feature-spec", "import-figma-assets", "device-usage",
          "figma-design-compare", "swiftui-adaptivity-check"}
SHARED = "_figma-full-cycle-shared"
CONSUMERS = {"figma-full-cycle", "figma-design-compare", "swiftui-adaptivity-check"}


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
        return ({entry.name for entry in self.target.iterdir() if (entry / "SKILL.md").is_file()}
                if self.target.exists() else set())

    def test_default_installs_all_six_entry_points_and_one_shared_resource_directory(self):
        result = self.run_install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.installed(), SKILLS)
        self.assertEqual({entry.name for entry in self.target.iterdir()}, SKILLS | {SHARED})
        for name in SKILLS:
            self.assertEqual((self.target / name).resolve(), ROOT / "skills" / name)

    def test_each_companion_can_be_installed_alone(self):
        for name in sorted(SKILLS - {"figma-full-cycle"}):
            with self.subTest(name=name):
                result = self.run_install("--skill", name)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.installed(), {name})
                if name in CONSUMERS:
                    self.assertTrue((self.target / SHARED / "scripts/screenshot_diff.py").is_file())
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
        self.assertTrue((self.target / SHARED).is_dir())

    def test_uninstall_one_validator_preserves_resources_for_the_other(self):
        result = self.run_install("--skill", "figma-design-compare", "--skill", "swiftui-adaptivity-check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.run_install("--uninstall", "--skill", "figma-design-compare").returncode, 0)
        self.assertEqual(self.installed(), {"swiftui-adaptivity-check"})
        self.assertTrue((self.target / SHARED / "scripts/screenshot_diff.py").is_file())

    def test_copied_standalone_validators_resolve_links_and_run_shared_cli_without_full_cycle(self):
        for name in ("figma-design-compare", "swiftui-adaptivity-check"):
            with self.subTest(name=name):
                target = Path(self.temp.name) / name / "isolated skills"
                result = subprocess.run(
                    ["bash", str(ROOT / "install.sh"), "--copy", "--target", str(target), "--skill", name],
                    text=True, capture_output=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual({entry.name for entry in target.iterdir()}, {name, SHARED})
                self.assertFalse(any(entry.is_symlink() for entry in target.rglob("*")))
                for doc in target.rglob("*.md"):
                    for link in re.findall(r"\[[^\]]*\]\(([^)\s]+)\)", doc.read_text()):
                        if link.startswith(("http:", "https:", "mailto:", "#")) or any(
                            marker in link for marker in ("{{", "<", "$")):
                            continue
                        self.assertTrue((doc.parent / link.split("#", 1)[0]).resolve().exists(),
                                        "{}: {}".format(doc, link))
                for helper in ("screenshot_diff.py", "ui_guard.py", "localization_context.py"):
                    command = subprocess.run(
                        [sys.executable, str(target / SHARED / "scripts" / helper), "--help"],
                        cwd=self.temp.name, text=True, capture_output=True,
                    )
                    self.assertEqual(command.returncode, 0, command.stderr)

    def test_missing_shared_resources_fail_before_any_install(self):
        isolated = Path(self.temp.name) / "incomplete source"
        isolated.mkdir()
        shutil.copyfile(ROOT / "install.sh", isolated / "install.sh")
        source_skill = isolated / "skills" / "figma-full-cycle"
        source_skill.mkdir(parents=True)
        (source_skill / "SKILL.md").write_text("---\nname: figma-full-cycle\n---\n")
        for name in ("figma-feature-spec", "import-figma-assets", "figma-design-compare", "swiftui-adaptivity-check"):
            skill = isolated / "skills" / name
            skill.mkdir()
            (skill / "SKILL.md").write_text("---\nname: {}\n---\n".format(name))
        result = subprocess.run(
            ["bash", str(isolated / "install.sh"), "--target", str(self.target), "--skill", "figma-full-cycle"],
            text=True, capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.target.exists())

    def test_incomplete_existing_shared_directory_requires_force_before_install(self):
        existing = self.target / SHARED
        existing.mkdir(parents=True)
        (existing / "sentinel").write_text("preserve until replacement is authorized")
        result = self.run_install("--copy", "--skill", "swiftui-adaptivity-check")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.installed(), set())
        self.assertTrue((existing / "sentinel").is_file())
        result = self.run_install("--copy", "--force", "--skill", "swiftui-adaptivity-check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((existing / "scripts/screenshot_diff.py").is_file())
        backups = list((self.target.parent / ".skill-backups").glob(SHARED + ".bak-*"))
        self.assertEqual(len(backups), 1)
        self.assertTrue((backups[0] / "sentinel").is_file())

    def test_copy_converts_owned_shared_symlinks_for_mixed_mode_installations(self):
        for force in ((), ("--force",)):
            with self.subTest(force=force):
                target = Path(self.temp.name) / ("forced" if force else "default")
                command = ["bash", str(ROOT / "install.sh"), "--target", str(target)]
                result = subprocess.run(command + ["--skill", "figma-design-compare"],
                                        text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue((target / SHARED).is_symlink())
                result = subprocess.run(command + ["--copy", *force, "--skill", "swiftui-adaptivity-check"],
                                        text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse((target / SHARED).is_symlink())
                self.assertFalse((target / "swiftui-adaptivity-check").is_symlink())
                for helper in ("screenshot_diff.py", "ui_guard.py", "localization_context.py"):
                    self.assertEqual((target / SHARED / "scripts" / helper).read_bytes(),
                                     (ROOT / "skills" / SHARED / "scripts" / helper).read_bytes())

    def test_copy_converts_an_owned_skill_symlink_without_force(self):
        self.assertEqual(self.run_install("--skill", "figma-design-compare").returncode, 0)
        result = self.run_install("--copy", "--skill", "figma-design-compare")
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ("figma-design-compare", SHARED):
            self.assertFalse((self.target / name).is_symlink())

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
