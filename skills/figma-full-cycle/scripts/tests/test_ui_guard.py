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


class TestNamedConstants(GuardTestCase):
    """A value with a name is still the value. Literal-only detection missed the
    canonical fixed-canvas case while reporting dozens of lesser findings."""

    LITERAL = (
        "struct V: View { var body: some View {\n"
        '    Text("x")\n'
        "        .frame(width: 393, height: 852)\n"
        "        .scaleEffect(0.9)\n"
        "        .offset(x: 12, y: 34)\n"
        "} }\n"
    )

    NAMED = (
        "enum K {\n"
        "    static let w: CGFloat = 393\n"
        "    static let h: CGFloat = 852\n"
        "    static let s: CGFloat = 0.9\n"
        "    static let dx: CGFloat = 12\n"
        "    static let dy: CGFloat = 34\n"
        "}\n"
        "struct V: View { var body: some View {\n"
        '    Text("x")\n'
        "        .frame(width: K.w, height: K.h)\n"
        "        .scaleEffect(K.s)\n"
        "        .offset(x: K.dx, y: K.dy)\n"
        "} }\n"
    )

    def test_named_constants_find_what_literals_find(self) -> None:
        literal = sorted(self.rules_for(self.LITERAL))
        named = sorted(self.rules_for(self.NAMED))

        self.assertEqual(literal, named)
        self.assertIn("LAY-01", named)

    def test_a_constant_defined_through_another_constant_resolves(self) -> None:
        rules = self.rules_for(
            "enum GeometryData {\n"
            "    static let referenceCanvasWidth: CGFloat = 393\n"
            "    static let referenceCanvasHeight: CGFloat = 852\n"
            "}\n"
            "enum OnboardingLayout {\n"
            "    static let width = GeometryData.referenceCanvasWidth\n"
            "    static let height = GeometryData.referenceCanvasHeight\n"
            "}\n"
            "struct V: View { var body: some View {\n"
            '    Text("x")\n'
            "        .frame(width: OnboardingLayout.width, height: OnboardingLayout.height)\n"
            "        .scaleEffect(canvasScale)\n"
            "} }\n",
            "--reference-canvas",
            "393x852",
        )

        self.assertIn("LAY-01", rules)
        self.assertIn("LAY-03", rules)

    def test_the_resolved_value_appears_in_the_message(self) -> None:
        self.write("View.swift", self.NAMED)
        result = self.check("View.swift")

        self.assertIn("K.w = 393", result.stderr)

    def test_an_unresolvable_pinned_frame_still_raises_the_canvas(self) -> None:
        rules = self.rules_for(
            "struct V: View { var body: some View {\n"
            '    Text("x")\n'
            "        .frame(width: someWidth, height: someHeight)\n"
            "        .scaleEffect(scale)\n"
            "} }\n"
        )

        self.assertIn("LAY-01", rules)

    def test_a_stretching_frame_is_not_a_canvas(self) -> None:
        rules = self.rules_for(
            "struct V: View { var body: some View {\n"
            '    Text("x")\n'
            "        .frame(maxWidth: .infinity, maxHeight: .infinity)\n"
            "        .scaleEffect(0.9)\n"
            "} }\n"
        )

        self.assertNotIn("LAY-01", rules)

    def test_an_icon_sized_frame_is_not_a_canvas(self) -> None:
        rules = self.rules_for(
            "struct V: View { var body: some View {\n"
            '    Text("x")\n'
            '    Image("badge")\n'
            "        .frame(width: 24, height: 24)\n"
            "        .scaleEffect(0.9)\n"
            "} }\n"
        )

        self.assertNotIn("LAY-01", rules)

    def test_a_name_holding_two_different_values_does_not_resolve(self) -> None:
        rules = self.rules_for(
            "enum A { static let size: CGFloat = 393 }\n"
            "enum B { static let size: CGFloat = 24 }\n"
            "struct V: View { var body: some View {\n"
            '    Image("badge").frame(width: size, height: size)\n'
            "} }\n"
        )

        self.assertNotIn("LAY-03", rules)


class TestCanvasResolution(GuardTestCase):
    """The shapes a real project writes a reference canvas in. Every one of these
    was silent in the first fix, whose fixtures only used literals in one file —
    including, fatally, only ever without --reference-canvas."""

    VIEW = (
        "struct OnboardingView: View {\n"
        "    var body: some View {\n"
        '        Text("Welcome")\n'
        "            .frame(width: OnboardingLayout.width, height: OnboardingLayout.height)\n"
        "            .scaleEffect(canvasScale)\n"
        "    }\n"
        "}\n"
    )

    CGSIZE_CONSTANTS = (
        "enum GeometryData {\n"
        "    static let referenceCanvasSize = CGSize(width: 393, height: 852)\n"
        "}\n"
        "enum OnboardingLayout {\n"
        "    static let width = GeometryData.referenceCanvasSize.width\n"
        "    static let height = GeometryData.referenceCanvasSize.height\n"
        "}\n"
    )

    def test_a_cgsize_member_behind_a_chain_resolves(self) -> None:
        rules = self.rules_for(
            self.CGSIZE_CONSTANTS + self.VIEW, "--reference-canvas", "393x852"
        )

        self.assertIn("LAY-01", rules)
        self.assertIn("LAY-03", rules)

    def test_a_one_line_enum_declaration_is_collected(self) -> None:
        rules = self.rules_for(
            "enum K { static let w: CGFloat = 393 }\n"
            "enum K2 { static let h: CGFloat = 852 }\n"
            "struct V: View { var body: some View {\n"
            '    Text("x")\n'
            "        .frame(width: K.w, height: K2.h)\n"
            "        .scaleEffect(scale)\n"
            "} }\n",
            "--reference-canvas",
            "393x852",
        )

        self.assertIn("LAY-01", rules)
        self.assertIn("LAY-03", rules)

    def test_constants_resolve_across_the_files_in_the_run(self) -> None:
        self.write("Style.swift", self.CGSIZE_CONSTANTS)
        self.write("Screen.swift", self.VIEW)
        result = self.check(
            "Style.swift", "Screen.swift", "--reference-canvas", "393x852", "--format", "json"
        )
        payload = json.loads(result.stdout)
        rules = {item["rule"] for item in payload["findings"]}

        self.assertIn("LAY-01", rules)
        self.assertIn("LAY-03", rules)

    def test_the_reference_canvas_flag_does_not_disable_the_fallback(self) -> None:
        # The flag documented as sharpening LAY-01 used to switch it off for any
        # size the resolver could not read.
        body = (
            "struct V: View { var body: some View {\n"
            '    Text("x")\n'
            "        .frame(width: someWidth, height: someHeight)\n"
            "        .scaleEffect(scale)\n"
            "} }\n"
        )

        self.assertIn("LAY-01", self.rules_for(body))
        self.assertIn("LAY-01", self.rules_for(body, "--reference-canvas", "393x852"))

    def test_artwork_narrower_than_the_screen_is_not_a_canvas(self) -> None:
        rules = self.rules_for(
            "struct V: View { var body: some View {\n"
            '    Image("art")\n'
            "        .frame(width: 381, height: 373)\n"
            "        .scaleEffect(0.9)\n"
            "} }\n",
            "--reference-canvas",
            "393x852",
        )

        self.assertNotIn("LAY-01", rules)


class TestFindingAnchoring(GuardTestCase):
    """A finding must land on the line carrying the modifier: anchoring at the
    chain start put waivers out of reach and moved when a comment was added."""

    CHAIN = (
        "struct V: View { var body: some View {\n"  # 1
        '    Text("x")\n'  # 2
        "        .frame(width: 393, height: 852)\n"  # 3
        "        .scaleEffect(0.9)\n"  # 4
        "        .offset(x: 12, y: 34)\n"  # 5
        "} }\n"
    )

    def lines_by_rule(self, body: str) -> dict:
        self.write("View.swift", body)
        result = self.check("View.swift", "--format", "json")
        payload = json.loads(result.stdout)
        mapping: dict = {}
        for item in payload["findings"]:
            mapping.setdefault(item["rule"], set()).add(item["line"])
        return mapping

    def test_each_finding_lands_on_its_own_modifier(self) -> None:
        lines = self.lines_by_rule(self.CHAIN)

        self.assertEqual(lines["LAY-03"], {3})
        self.assertEqual(lines["LAY-09"], {4})
        self.assertEqual(lines["LAY-04"], {5})

    def test_a_finding_after_a_closing_paren_still_lands_on_its_line(self) -> None:
        lines = self.lines_by_rule(
            "struct V: View { var body: some View {\n"  # 1
            '    Text("x")\n'  # 2
            "        .frame(\n"  # 3
            "            maxWidth: .infinity\n"  # 4
            "        )\n"  # 5
            "        .offset(x: 12, y: 34)\n"  # 6
            "} }\n"
        )

        self.assertEqual(lines["LAY-04"], {6})

    def test_a_waiver_above_the_modifier_works(self) -> None:
        self.write(
            "View.swift",
            "struct V: View { var body: some View {\n"
            '    Text("x")\n'
            "        .frame(maxWidth: .infinity)\n"
            "        // ui-guard: allow LAY-04 — animated entrance, reset on completion\n"
            "        .offset(x: 12, y: 34)\n"
            "} }\n",
        )
        result = self.check("View.swift")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1 waived", result.stdout)

    def test_a_waiver_on_the_modifier_line_works(self) -> None:
        self.write(
            "View.swift",
            "struct V: View { var body: some View {\n"
            '    Text("x")\n'
            "        .frame(maxWidth: .infinity)\n"
            "        .offset(x: 12, y: 34) // ui-guard: allow LAY-04 — animated entrance\n"
            "} }\n",
        )
        result = self.check("View.swift")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1 waived", result.stdout)


class TestScaleEffectScope(GuardTestCase):
    def test_press_feedback_in_a_button_style_is_not_a_finding(self) -> None:
        rules = self.rules_for(
            "struct CardButtonStyle: ButtonStyle {\n"
            "    func makeBody(configuration: Configuration) -> some View {\n"
            "        configuration.label\n"
            "            .padding(16)\n"
            "            .scaleEffect(configuration.isPressed ? 0.97 : 1)\n"
            "    }\n"
            "}\n"
            'struct Card: View { var body: some View { Text("Continue") } }\n'
        )

        self.assertNotIn("LAY-09", rules)

    def test_a_static_scale_over_text_is_still_a_finding(self) -> None:
        rules = self.rules_for(
            "struct V: View { var body: some View {\n"
            '    Text("x").scaleEffect(canvasScale)\n'
            "} }\n"
        )

        self.assertIn("LAY-09", rules)

    def test_a_file_without_text_is_left_alone(self) -> None:
        rules = self.rules_for(
            "struct V: View { var body: some View {\n"
            '    Image("decor").scaleEffect(0.9)\n'
            "} }\n"
        )

        self.assertNotIn("LAY-09", rules)


class TestCompositions(GuardTestCase):
    """Fixed-size artwork places its elements against each other, not against the
    screen. One marker covers the block; a waiver per element would just train
    the reflex to waive."""

    ARTWORK = (
        "struct AnimalsGroup: View {\n"  # 1
        "    var body: some View {\n"  # 2
        "        // ui-guard: composition OnboardingAnimals — 280x180 artwork, anchored by the parent\n"  # 3
        "        ZStack {\n"  # 4
        '            Image("cat").offset(x: -84.1, y: 0.4)\n'  # 5
        '            Image("dog").offset(x: 8)\n'  # 6
        '            Image("bird").offset(x: 65.5)\n'  # 7
        "        }\n"  # 8
        "        .frame(width: 280, height: 180)\n"  # 9
        "    }\n"
        "}\n"
    )

    def test_placement_inside_a_composition_is_exempt(self) -> None:
        self.assertNotIn("LAY-04", self.rules_for(self.ARTWORK))

    def test_placement_outside_it_is_still_caught(self) -> None:
        rules = self.rules_for(
            self.ARTWORK
            + "struct Elsewhere: View {\n"
            + "    var body: some View {\n"
            + '        Image("badge").offset(x: 12, y: 4)\n'
            + "    }\n"
            + "}\n"
        )

        self.assertIn("LAY-04", rules)

    def test_exemptions_are_announced_with_their_lines(self) -> None:
        self.write("View.swift", self.ARTWORK)
        result = self.check("View.swift")

        self.assertIn("composition 'OnboardingAnimals'", result.stdout)
        self.assertIn("3 fixed-geometry finding(s)", result.stdout)
        self.assertIn("3 exempt by composition", result.stdout)

    def test_a_screen_sized_composition_is_refused(self) -> None:
        self.write(
            "View.swift",
            "struct FakeComposition: View {\n"
            "    var body: some View {\n"
            "        // ui-guard: composition WholeScreen — totally artwork honest\n"
            "        ZStack {\n"
            '            Image("a").offset(x: 40, y: 100)\n'
            '            Image("b").position(x: 200, y: 400)\n'
            "        }\n"
            "        .frame(width: 393, height: 852)\n"
            "    }\n"
            "}\n",
        )
        result = self.check("View.swift", "--reference-canvas", "393x852")

        self.assertIn("a canvas is not artwork", result.stderr)
        self.assertIn("0 exempt by composition", result.stdout)
        self.assertIn("static .offset(x: 40, y: 100)", result.stderr)
        self.assertIn(".position(...)", result.stderr)

    def test_a_canvas_behind_a_cgsize_constant_is_also_refused(self) -> None:
        # The literal case was refused from the start; the same canvas written as
        # a constant walked straight through, which made the marker a way to
        # legalise a fixed canvas one comment at a time.
        self.write(
            "View.swift",
            "enum IGeo {\n"
            "    static let canvas = CGSize(width: 393, height: 852)\n"
            "}\n"
            "struct Fake: View {\n"
            "    var body: some View {\n"
            "        // ui-guard: composition FakeArtwork — totally artwork\n"
            "        ZStack {\n"
            '            Image("a").offset(x: 40, y: 100)\n'
            '            Image("b").position(x: 200, y: 400)\n'
            "        }\n"
            "        .frame(width: IGeo.canvas.width, height: IGeo.canvas.height)\n"
            "    }\n"
            "}\n",
        )
        result = self.check("View.swift", "--reference-canvas", "393x852")

        self.assertIn("a canvas is not artwork", result.stderr)
        self.assertIn("0 exempt by composition", result.stdout)

    def test_artwork_wider_than_the_old_threshold_is_still_honoured(self) -> None:
        # 381pt on a 393pt canvas: under the bare `>= 300` rule this honest
        # illustration was refused as screen-sized.
        self.write(
            "View.swift",
            "struct BadgeScatter: View {\n"
            "    var body: some View {\n"
            "        // ui-guard: composition BadgeScatter — 381x373 cluster\n"
            "        ZStack {\n"
            '            Image("vial").offset(x: -141.5, y: -110.9)\n'
            "        }\n"
            "        .frame(width: 381, height: 373)\n"
            "    }\n"
            "}\n",
        )
        result = self.check("View.swift", "--reference-canvas", "393x852")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("composition 'BadgeScatter'", result.stdout)

    def test_the_block_size_frame_is_exempt_too(self) -> None:
        rules = self.rules_for(
            "struct A: View { var body: some View {\n"
            "    // ui-guard: composition Art — 381x373 cluster\n"
            "    ZStack {\n"
            '        Image("v").offset(x: -141.5)\n'
            "    }\n"
            "    .frame(width: 381, height: 373)\n"
            "} }\n",
            "--reference-canvas",
            "393x852",
        )

        self.assertNotIn("LAY-03", rules)

    def test_a_marker_that_exempts_nothing_says_so(self) -> None:
        self.write(
            "View.swift",
            "struct D: View { var body: some View {\n"
            "    // ui-guard: composition Leftover — nothing here any more\n"
            "    VStack {\n"
            '        Text("hello")\n'
            "    }\n"
            "} }\n",
        )
        result = self.check("View.swift")

        self.assertIn("composition 'Leftover' exempts 0", result.stdout)

    def test_a_refused_marker_is_not_also_reported_as_empty(self) -> None:
        self.write(
            "View.swift",
            "struct Fake: View { var body: some View {\n"
            "    // ui-guard: composition Fake — nope\n"
            "    ZStack {\n"
            '        Image("a").offset(x: 40, y: 100)\n'
            "    }\n"
            "    .frame(width: 393, height: 852)\n"
            "} }\n",
        )
        result = self.check("View.swift", "--reference-canvas", "393x852")

        self.assertNotIn("exempts 0", result.stdout)

    def test_the_reason_is_not_taken_as_the_name(self) -> None:
        self.write("View.swift", self.ARTWORK)
        result = self.check("View.swift", "--format", "json")
        payload = json.loads(result.stdout)

        names = {item["composition"] for item in payload["composition_exemptions"]}
        self.assertEqual(names, {"OnboardingAnimals"})


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

    def test_truncated_output_names_the_flag_that_lifts_it(self) -> None:
        self.write(
            "View.swift",
            "struct V: View { var body: some View {\n"
            + "".join(
                '    Image("i{}").position(x: 1, y: 2)\n'.format(index) for index in range(6)
            )
            + "} }\n",
        )
        result = self.check("View.swift", "--max-findings", "2")

        self.assertIn("--max-findings", result.stderr)
        self.assertIn("--format json", result.stderr)

    def test_the_markers_are_documented_in_help(self) -> None:
        result = run("check", "--help")

        self.assertIn("UI_GUARD_CLEAN", result.stdout)
        self.assertIn("ui-guard: composition", result.stdout)

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
