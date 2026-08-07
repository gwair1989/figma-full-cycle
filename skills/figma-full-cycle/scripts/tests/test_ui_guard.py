#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]
CLI = SKILL_ROOT / "scripts" / "ui_guard.py"


CLEAN_VIEW = """
import SwiftUI

struct GoodView: View {
    var body: some View {
        VStack(spacing: 12) {
            Text("Hello")
                .foregroundStyle(Theme.textPrimary)
            Image("badge")
                .frame(width: 24, height: 24)
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .background(Theme.surface.ignoresSafeArea())
    }
}
"""


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), "check", *args],
        text=True,
        capture_output=True,
        check=False,
    )


class GuardTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def write(self, name: str, body: str) -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    def check(self, *extra: str) -> subprocess.CompletedProcess:
        return run("--project-root", str(self.root), *extra)

    def rules_for(self, body: str, *extra: str) -> list:
        self.write("View.swift", body)
        result = self.check("View.swift", "--format", "json", *extra)
        payload = json.loads(result.stdout)
        return [item["rule"] for item in payload["findings"] if not item["waived"]]


class TestCleanSources(GuardTestCase):
    def test_idiomatic_view_is_clean(self) -> None:
        self.write("View.swift", CLEAN_VIEW)
        result = self.check("View.swift")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("UI_GUARD_CLEAN", result.stdout)

    def test_clean_run_states_what_it_did_not_check(self) -> None:
        self.write("View.swift", CLEAN_VIEW)
        result = self.check("View.swift")

        self.assertIn("reviewer  LAY-07", result.stdout)
        self.assertIn("reviewer  COL-03", result.stdout)

    def test_non_swift_files_are_ignored(self) -> None:
        self.write("notes.md", "Color(red: 1, green: 0, blue: 0)")
        result = self.check("notes.md")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("0 files scanned", result.stdout)


class TestLayoutRules(GuardTestCase):
    def test_fixed_canvas_with_scale_effect(self) -> None:
        rules = self.rules_for(
            "struct V: View { var body: some View {\n"
            "    Group { EmptyView() }\n"
            "        .frame(width: 393, height: 852)\n"
            "        .scaleEffect(0.9)\n"
            "} }\n"
        )
        self.assertIn("LAY-01", rules)

    def test_hard_frame_on_greedy_shape(self) -> None:
        rules = self.rules_for(
            "struct V: View { var body: some View {\n"
            "    Rectangle()\n"
            "        .frame(width: 120, height: 44)\n"
            "} }\n"
        )
        self.assertIn("LAY-02", rules)

    def test_image_frame_is_not_a_greedy_shape(self) -> None:
        rules = self.rules_for(
            "struct V: View { var body: some View {\n"
            '    Image("badge")\n'
            "        .frame(width: 24, height: 24)\n"
            "} }\n"
        )
        self.assertNotIn("LAY-02", rules)

    def test_derived_width_is_reported(self) -> None:
        rules = self.rules_for(
            "struct V: View { var body: some View {\n"
            "    Group { EmptyView() }.frame(width: 393 - 32)\n"
            "} }\n"
        )
        self.assertIn("LAY-03", rules)

    def test_position_is_reported(self) -> None:
        rules = self.rules_for(
            "struct V: View { var body: some View {\n"
            '    Image("badge").position(x: 12, y: 40)\n'
            "} }\n"
        )
        self.assertIn("LAY-04", rules)

    def test_static_offset_is_reported_but_animated_offset_is_not(self) -> None:
        static_rules = self.rules_for(
            "struct V: View { var body: some View {\n"
            '    Text("x").offset(y: 12)\n'
            "} }\n"
        )
        self.assertIn("LAY-04", static_rules)

        animated_rules = self.rules_for(
            "struct V: View { var body: some View {\n"
            '    Text("x").offset(y: 12).animation(.default, value: isAnimating)\n'
            "} }\n"
        )
        self.assertNotIn("LAY-04", animated_rules)

    def test_background_before_stretch(self) -> None:
        rules = self.rules_for(
            "struct V: View { var body: some View {\n"
            "    VStack { EmptyView() }\n"
            "        .background(Theme.surface)\n"
            "        .frame(maxWidth: .infinity, maxHeight: .infinity)\n"
            "} }\n"
        )
        self.assertIn("LAY-08", rules)

    def test_background_after_stretch_is_clean(self) -> None:
        rules = self.rules_for(
            "struct V: View { var body: some View {\n"
            "    VStack { EmptyView() }\n"
            "        .frame(maxWidth: .infinity, maxHeight: .infinity)\n"
            "        .background(Theme.surface)\n"
            "} }\n"
        )
        self.assertNotIn("LAY-08", rules)

    def test_geometry_arithmetic_needs_a_derivation(self) -> None:
        undocumented = self.rules_for(
            "struct V: View { var body: some View {\n"
            '    Text("x").offset(y: -safeAreaInsets.top / 2)\n'
            "} }\n"
        )
        self.assertIn("LAY-10", undocumented)

        documented = self.rules_for(
            "struct V: View { var body: some View {\n"
            "    // centring inside the reduced safe area: -(top - bottom) / 2\n"
            '    Text("x").offset(y: -(safeAreaInsets.top - safeAreaInsets.bottom) / 2)\n'
            "} }\n"
        )
        self.assertNotIn("LAY-10", documented)


class TestColorRules(GuardTestCase):
    def test_every_literal_form_is_detected(self) -> None:
        forms = (
            "Color(red: 1, green: 0, blue: 0)",
            "Color(white: 0.5)",
            "Color(hue: 0.1, saturation: 1, brightness: 1)",
            "Color(hex: 0xDB69FF)",
            "UIColor(red: 1, green: 0, blue: 0, alpha: 1)",
            "UIColor(white: 0.2, alpha: 1)",
            "UIColor(displayP3Red: 1, green: 0, blue: 0, alpha: 1)",
            "NSColor(calibratedRed: 1, green: 0, blue: 0, alpha: 1)",
            "#colorLiteral(red: 1, green: 0, blue: 0, alpha: 1)",
            'Color("#DB69FF")',
        )
        for form in forms:
            with self.subTest(form=form):
                rules = self.rules_for(
                    "struct V: View { var body: some View {\n"
                    '    Text("x").foregroundStyle(' + form + ")\n"
                    "} }\n"
                )
                self.assertIn("COL-05", rules)

    def test_named_asset_color_is_not_a_literal(self) -> None:
        rules = self.rules_for(
            "struct V: View { var body: some View {\n"
            '    Text("x").foregroundStyle(Color("BrandSurface"))\n'
            "} }\n"
        )
        self.assertNotIn("COL-05", rules)

    def test_preview_literal_is_marked_as_preview_context(self) -> None:
        self.write(
            "View.swift",
            "struct V: View { var body: some View { EmptyView() } }\n"
            "\n"
            "#Preview {\n"
            "    V().background(Color(white: 0.95))\n"
            "}\n",
        )
        result = self.check("View.swift", "--format", "json")
        payload = json.loads(result.stdout)
        contexts = [item["context"] for item in payload["findings"] if item["rule"] == "COL-05"]

        self.assertEqual(contexts, ["preview"])

    def test_palette_symbol_outside_the_semantic_layer(self) -> None:
        self.write(
            "Views/Screen.swift",
            "struct V: View { var body: some View {\n"
            '    Text("x").foregroundStyle(Color.hexDB69FF)\n'
            "} }\n",
        )
        self.write(
            "DesignSystem/Theme.swift",
            "enum Theme { static let accent = Color.hexDB69FF }\n",
        )

        result = self.check(
            "Views/Screen.swift",
            "DesignSystem/Theme.swift",
            "--palette-symbol",
            "hexDB69FF",
            "--semantic-layer",
            "DesignSystem/*.swift",
            "--format",
            "json",
        )
        payload = json.loads(result.stdout)
        paths = [item["path"] for item in payload["findings"] if item["rule"] == "COL-01"]

        self.assertEqual(paths, ["Views/Screen.swift"])

    def test_duplicate_and_alpha_palette_entries(self) -> None:
        def colorset(name: str, components: dict) -> None:
            payload = {
                "colors": [{"color": {"color-space": "srgb", "components": components}}],
                "info": {"author": "xcode", "version": 1},
            }
            path = self.root / "Assets.xcassets" / (name + ".colorset") / "Contents.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload), encoding="utf-8")

        opaque = {"red": "0.859", "green": "0.412", "blue": "1.000", "alpha": "1.000"}
        colorset("brandPurple", opaque)
        colorset("accentPurple", dict(opaque))
        colorset("brandPurpleAlpha16", dict(opaque, alpha="0.160"))

        result = self.check(
            "--asset-catalog", "Assets.xcassets", "--rules", "COL", "--format", "json"
        )
        payload = json.loads(result.stdout)
        rules = sorted({item["rule"] for item in payload["findings"]})

        self.assertEqual(rules, ["COL-02", "COL-04"])
        self.assertFalse(payload["clean"])


class TestWaiversAndPlumbing(GuardTestCase):
    def test_waiver_comment_suppresses_the_finding(self) -> None:
        self.write(
            "View.swift",
            "struct V: View { var body: some View {\n"
            '    Text("x")\n'
            "        // ui-guard: allow LAY-04 — animated entrance, reset on completion\n"
            "        .offset(y: 12)\n"
            "} }\n",
        )
        result = self.check("View.swift")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1 waived", result.stdout)

    def test_waiver_only_covers_its_own_rule(self) -> None:
        self.write(
            "View.swift",
            "struct V: View { var body: some View {\n"
            "    // ui-guard: allow COL-05 — unrelated waiver\n"
            '    Image("badge").position(x: 1, y: 2)\n'
            "} }\n",
        )
        result = self.check("View.swift")

        self.assertEqual(result.returncode, 1)
        self.assertIn("LAY-04", result.stderr)

    def test_bad_reference_canvas_is_a_usage_error(self) -> None:
        result = self.check("--reference-canvas", "393")

        self.assertEqual(result.returncode, 2)
        self.assertIn("WIDTHxHEIGHT", result.stderr)

    def test_changed_since_reads_the_git_diff(self) -> None:
        git = ["git", "-C", str(self.root)]
        subprocess.run(git + ["init", "-q"], check=True, capture_output=True)
        subprocess.run(git + ["config", "user.email", "t@example.com"], check=True)
        subprocess.run(git + ["config", "user.name", "t"], check=True)
        self.write("View.swift", CLEAN_VIEW)
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(git + ["commit", "-qm", "base"], check=True, capture_output=True)

        self.write(
            "Broken.swift",
            "struct V: View { var body: some View {\n"
            '    Image("badge").position(x: 1, y: 2)\n'
            "} }\n",
        )
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(git + ["commit", "-qm", "change"], check=True, capture_output=True)

        result = self.check("--changed-since", "HEAD~1", "--format", "json")
        payload = json.loads(result.stdout)

        self.assertEqual(payload["files_scanned"], 1)
        self.assertEqual([item["rule"] for item in payload["findings"]], ["LAY-04"])

    def test_json_reports_the_rules_it_ran(self) -> None:
        self.write("View.swift", CLEAN_VIEW)
        result = self.check("View.swift", "--rules", "LAY", "--format", "json")
        payload = json.loads(result.stdout)

        self.assertTrue(payload["clean"])
        self.assertTrue(all(rule.startswith("LAY") for rule in payload["checked_rules"]))
        self.assertTrue(all(rule.startswith("LAY") for rule in payload["reviewer_rules"]))


if __name__ == "__main__":
    unittest.main()
