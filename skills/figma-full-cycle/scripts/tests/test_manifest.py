#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]
CLI = SKILL_ROOT / "scripts" / "manifest.py"
TEMPLATE = SKILL_ROOT / "templates" / "PIPELINE.template.md"


MANIFEST = """# F — Pipeline manifest

## Capability ledger (preflight)

| Role | Binding |
|------|---------|
| `feature-spec` | `figma-feature-spec` |

### Figma access probe

probe ok

## Project UI convention contract (preflight)

| Area | Project sources (path + section/symbol) | Status |
|------|------------------------------------------|--------|
| Layout | `docs/architecture.md#layout @ {layout}` | `project-specific` |
| Colors | `docs/colors.md @ {colors}` | `matched` |
| Typography | | `todo` |

## Stages

| # | Stage |
|---|-------|
| 1 | Spec |
"""


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        text=True,
        capture_output=True,
        check=False,
    )


class ManifestTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        (self.root / "docs").mkdir()

    def write(self, name: str, body: str) -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    def digest_of(self, *names: str) -> list:
        result = run("digest", "--project-root", str(self.root), *names)
        self.assertEqual(result.returncode, 0, result.stderr)
        return [line.split(" @ ")[1] for line in result.stdout.strip().splitlines()]

    def build_manifest(self) -> Path:
        self.write("docs/architecture.md", "canvas rules\n")
        self.write("docs/colors.md", "palette rules\n")
        layout, colors = self.digest_of("docs/architecture.md", "docs/colors.md")
        return self.write("docs/F_PIPELINE.md", MANIFEST.format(layout=layout, colors=colors))


class TestSections(ManifestTestCase):
    def test_lists_headings_with_nesting(self) -> None:
        manifest = self.build_manifest()
        result = run("sections", "--file", str(manifest))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Capability ledger (preflight)", result.stdout)
        self.assertIn("  Figma access probe", result.stdout)
        self.assertIn("5 sections", result.stdout)

    def test_headings_inside_code_fences_are_not_sections(self) -> None:
        manifest = self.write(
            "docs/F_PIPELINE.md",
            "# Title\n\n## Real\n\n```bash\n# not a heading\n```\n",
        )
        result = run("sections", "--file", str(manifest))

        self.assertIn("2 sections", result.stdout)


class TestGet(ManifestTestCase):
    def test_parent_section_brings_its_subsections(self) -> None:
        manifest = self.build_manifest()
        result = run("get", "--file", str(manifest), "--section", "Capability ledger")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Figma access probe", result.stdout)
        self.assertNotIn("Project UI convention contract", result.stdout)

    def test_matches_on_a_substring(self) -> None:
        manifest = self.build_manifest()
        result = run("get", "--file", str(manifest), "--section", "convention contract")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("| Layout |", result.stdout)

    def test_several_sections_print_in_file_order(self) -> None:
        manifest = self.build_manifest()
        result = run(
            "get", "--file", str(manifest), "--section", "Stages", "--section", "Capability ledger"
        )

        self.assertLess(result.stdout.index("Capability ledger"), result.stdout.index("## Stages"))

    def test_unknown_section_reports_what_exists(self) -> None:
        manifest = self.build_manifest()
        result = run("get", "--file", str(manifest), "--section", "Nope")

        self.assertEqual(result.returncode, 1)
        self.assertIn("no section matching: Nope", result.stderr)
        self.assertIn("available:", result.stderr)

    def test_missing_manifest_is_a_usage_error(self) -> None:
        result = run("get", "--file", str(self.root / "absent.md"), "--section", "Stages")

        self.assertEqual(result.returncode, 2)
        self.assertIn("manifest not found", result.stderr)


class TestDigest(ManifestTestCase):
    def test_digest_is_stable_and_changes_with_content(self) -> None:
        self.write("docs/a.md", "one\n")
        first = self.digest_of("docs/a.md")
        self.assertEqual(first, self.digest_of("docs/a.md"))

        self.write("docs/a.md", "two\n")
        self.assertNotEqual(first, self.digest_of("docs/a.md"))

    def test_missing_file_is_reported(self) -> None:
        result = run("digest", "--project-root", str(self.root), "docs/absent.md")

        self.assertEqual(result.returncode, 1)
        self.assertIn("missing: docs/absent.md", result.stderr)


class TestVerifySources(ManifestTestCase):
    def verify(self, manifest: Path) -> subprocess.CompletedProcess:
        return run("verify-sources", "--file", str(manifest), "--project-root", str(self.root))

    def test_unchanged_sources_pass_but_an_unrecorded_area_does_not(self) -> None:
        manifest = self.build_manifest()
        result = self.verify(manifest)

        self.assertIn("Layout         unchanged", result.stdout)
        self.assertIn("Colors         unchanged", result.stdout)
        self.assertIn("Typography     unrecorded", result.stdout)
        self.assertEqual(result.returncode, 1)

    def test_all_areas_recorded_and_unchanged_exits_zero(self) -> None:
        self.write("docs/architecture.md", "canvas rules\n")
        self.write("docs/colors.md", "palette rules\n")
        self.write("docs/type.md", "type rules\n")
        layout, colors, typography = self.digest_of(
            "docs/architecture.md", "docs/colors.md", "docs/type.md"
        )
        manifest = self.write(
            "docs/F_PIPELINE.md",
            MANIFEST.format(layout=layout, colors=colors).replace(
                "| Typography | | `todo` |",
                "| Typography | `docs/type.md @ {}` | `matched` |".format(typography),
            ),
        )

        result = self.verify(manifest)

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("all 3 areas unchanged", result.stdout)

    def test_changed_source_names_the_file_and_both_digests(self) -> None:
        manifest = self.build_manifest()
        self.write("docs/architecture.md", "canvas rules, rewritten\n")

        result = self.verify(manifest)

        self.assertIn("Layout         CHANGED", result.stdout)
        self.assertIn("docs/architecture.md (was ", result.stdout)
        self.assertIn("Colors         unchanged", result.stdout)
        self.assertEqual(result.returncode, 1)

    def test_deleted_source_is_reported_as_missing(self) -> None:
        manifest = self.build_manifest()
        (self.root / "docs" / "colors.md").unlink()

        result = self.verify(manifest)

        self.assertIn("docs/colors.md (missing)", result.stdout)
        self.assertEqual(result.returncode, 1)

    def test_manifest_without_a_contract_table_is_a_usage_error(self) -> None:
        manifest = self.write("docs/F_PIPELINE.md", "# Title\n\n## Stages\n\nnothing here\n")

        result = self.verify(manifest)

        self.assertEqual(result.returncode, 2)
        self.assertIn("no UI convention contract table", result.stderr)


class TestBundledTemplate(ManifestTestCase):
    def test_template_sections_are_addressable(self) -> None:
        result = run("sections", "--file", str(TEMPLATE))

        self.assertEqual(result.returncode, 0, result.stderr)
        for title in ("Capability ledger", "Stages", "Question log", "UI policy checks"):
            self.assertIn(title, result.stdout)

    def test_template_contract_areas_are_parsed(self) -> None:
        result = run("verify-sources", "--file", str(TEMPLATE), "--project-root", str(self.root))

        # The blank template records no digests yet: every area must come back
        # as `unrecorded`, never as silently unchanged.
        for area in ("Layout", "Strings", "Typography", "Colors", "Images", "Accessibility"):
            self.assertIn(area, result.stdout)
        self.assertIn("unrecorded", result.stdout)
        self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main()
