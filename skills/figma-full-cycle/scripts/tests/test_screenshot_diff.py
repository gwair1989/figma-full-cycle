#!/usr/bin/env python3

from __future__ import annotations

import json
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]
CLI = SKILL_ROOT / "scripts" / "screenshot_diff.py"

BACKGROUND = (30, 30, 40)
CARD = (220, 90, 60)
BAR = (255, 255, 255)

# Point sizes, not retina pixels: the fixtures are written by a pure-Python PNG
# writer, and the cross-size behaviour under test does not care about the scale.
MOCK_SIZE = (393, 852)
RENDER_SIZE = (375, 667)


def write_png(path: Path, width: int, height: int, pixel, alpha: bool = False) -> None:
    """Minimal stdlib PNG writer — fixtures, not a library."""
    channels = 4 if alpha else 3
    colour_type = 6 if alpha else 2
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter: none
        for x in range(width):
            values = pixel(x, y)
            raw.extend(values[:channels] if len(values) >= channels else tuple(values) + (255,))

    def chunk(tag: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + tag
            + payload
            + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
        )

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, colour_type, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
        + chunk(b"IEND", b"")
    )


def scaled_box(width: int, height: int, left: float, right: float, top: float, bottom: float):
    """A card occupying the same relative area at any canvas size."""

    def pixel(x: int, y: int):
        inside = left * width < x < right * width and top * height < y < bottom * height
        return CARD if inside else BACKGROUND

    return pixel


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), *args], text=True, capture_output=True, check=False
    )


@unittest.skipUnless(shutil.which("sips"), "sips is macOS-only; the script requires it")
class ScreenshotDiffTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

        self.mock = self.root / "mock.png"
        write_png(self.mock, *MOCK_SIZE, pixel=scaled_box(*MOCK_SIZE, 0.13, 0.87, 0.23, 0.74))

        self.render = self.root / "render.png"
        write_png(self.render, *RENDER_SIZE, pixel=scaled_box(*RENDER_SIZE, 0.13, 0.87, 0.23, 0.74))

    def compare(self, render: Path, *extra: str) -> subprocess.CompletedProcess:
        return run("compare", "--render", str(render), "--mock", str(self.mock), *extra)

    def verdict(self, render: Path, *extra: str) -> dict:
        result = self.compare(render, "--format", "json", *extra)
        self.assertIn(result.returncode, (0, 1), result.stderr)
        return json.loads(result.stdout)[0]

    def render_with(self, name: str, pixel) -> Path:
        path = self.root / name
        write_png(path, *RENDER_SIZE, pixel=pixel)
        return path


class TestCrossSizeComparison(ScreenshotDiffTestCase):
    def test_same_layout_at_a_different_size_and_aspect_passes(self) -> None:
        result = self.compare(self.render)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("SCREENSHOT_DIFF_CLEAN", result.stdout)
        self.assertIn("PASS", result.stdout)

    def test_identical_sizes_also_work(self) -> None:
        same = self.root / "same.png"
        write_png(same, *MOCK_SIZE, pixel=scaled_box(*MOCK_SIZE, 0.13, 0.87, 0.23, 0.74))

        self.assertTrue(self.verdict(same)["pass"])

    def test_every_run_states_what_it_cannot_see(self) -> None:
        result = self.compare(self.render)

        self.assertIn("Blind to:", result.stdout)
        self.assertIn("typeface", result.stdout)
        self.assertIn("one PASS per screen", result.stdout)


class TestDefectDetection(ScreenshotDiffTestCase):
    def test_pillarbox_is_detected(self) -> None:
        width, height = RENDER_SIZE
        inner = scaled_box(width, height, 0.22, 0.78, 0.23, 0.74)
        render = self.render_with(
            "pillarbox.png",
            lambda x, y: BAR if (x < width * 0.09 or x > width * 0.91) else inner(x, y),
        )

        verdict = self.verdict(render)

        self.assertTrue(verdict["pillarbox"])
        self.assertFalse(verdict["pass"])

    def test_letterbox_is_detected(self) -> None:
        width, height = RENDER_SIZE
        inner = scaled_box(width, height, 0.13, 0.87, 0.30, 0.67)
        render = self.render_with(
            "letterbox.png",
            lambda x, y: BAR if (y < height * 0.09 or y > height * 0.91) else inner(x, y),
        )

        verdict = self.verdict(render)

        self.assertTrue(verdict["letterbox"])
        self.assertFalse(verdict["pass"])

    def test_background_not_reaching_the_edges_is_detected(self) -> None:
        width, height = RENDER_SIZE
        inner = scaled_box(width, height, 0.13, 0.87, 0.23, 0.74)
        render = self.render_with(
            "inset-bg.png",
            lambda x, y: (250, 250, 250)
            if (x < width * 0.04 or x > width * 0.96 or y < height * 0.02 or y > height * 0.98)
            else inner(x, y),
        )

        verdict = self.verdict(render)

        self.assertFalse(verdict["bg_reaches_edges"])
        self.assertFalse(verdict["pass"])

    def test_content_clipped_at_the_bottom_is_detected(self) -> None:
        # The mock carries a bottom bar the render loses off the bottom edge —
        # what clipping actually looks like, as opposed to a shorter card.
        mock_width, mock_height = MOCK_SIZE
        base_mock = scaled_box(*MOCK_SIZE, 0.13, 0.87, 0.23, 0.74)
        write_png(
            self.mock,
            mock_width,
            mock_height,
            lambda x, y: CARD
            if (0.08 * mock_width < x < 0.92 * mock_width and 0.86 * mock_height < y < 0.95 * mock_height)
            else base_mock(x, y),
        )

        verdict = self.verdict(self.render)

        self.assertGreater(verdict["bottom_area_diff_cells"], 0)
        self.assertFalse(verdict["pass"])

    def test_failure_output_names_the_reasons(self) -> None:
        width, height = RENDER_SIZE
        inner = scaled_box(width, height, 0.22, 0.78, 0.23, 0.74)
        render = self.render_with(
            "pillarbox.png",
            lambda x, y: BAR if (x < width * 0.09 or x > width * 0.91) else inner(x, y),
        )

        result = self.compare(render)

        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL", result.stdout)
        self.assertIn("pillarbox", result.stdout)
        self.assertIn("SCREENSHOT_DIFF_DIRTY", result.stdout)


class TestIgnoreBands(ScreenshotDiffTestCase):
    def status_bar_render(self) -> Path:
        width, height = RENDER_SIZE
        inner = scaled_box(width, height, 0.13, 0.87, 0.23, 0.74)
        return self.render_with(
            "statusbar.png",
            lambda x, y: (0, 0, 0) if y < height * 0.05 else inner(x, y),
        )

    def test_a_band_present_only_in_the_render_fails_by_default(self) -> None:
        self.assertFalse(self.verdict(self.status_bar_render())["pass"])

    def test_ignoring_that_band_clears_it(self) -> None:
        verdict = self.verdict(self.status_bar_render(), "--ignore-top", "6%")

        self.assertTrue(verdict["pass"], verdict)

    def test_pixels_and_percentages_are_both_accepted(self) -> None:
        render = self.status_bar_render()
        by_percent = self.verdict(render, "--ignore-top", "6%")
        by_pixels = self.verdict(render, "--ignore-top", "80")

        self.assertEqual(by_percent["pass"], by_pixels["pass"])

    def test_ignoring_everything_is_an_error(self) -> None:
        result = self.compare(self.render, "--ignore-top", "60%", "--ignore-bottom", "60%")

        self.assertEqual(result.returncode, 2)
        self.assertIn("nothing to compare", result.stderr)


class TestReportingAndPlumbing(ScreenshotDiffTestCase):
    def test_out_writes_the_full_report_and_stdout_stays_short(self) -> None:
        out = self.root / "reports" / "diff.json"
        result = self.compare(self.render, "--out", str(out))

        self.assertTrue(out.is_file())
        payload = json.loads(out.read_text(encoding="utf-8"))
        self.assertIn("checks", payload[0])
        self.assertIn("edge_bands", payload[0]["checks"])
        self.assertNotIn("edge_bands", result.stdout)

    def test_json_format_prints_verdicts_only(self) -> None:
        result = self.compare(self.render, "--format", "json")
        payload = json.loads(result.stdout)

        self.assertEqual(len(payload), 1)
        self.assertIn("pass", payload[0])
        self.assertNotIn("checks", payload[0])

    def test_alpha_input_is_flagged(self) -> None:
        width, height = RENDER_SIZE
        inner = scaled_box(width, height, 0.13, 0.87, 0.23, 0.74)
        render = self.root / "alpha.png"
        write_png(render, width, height, lambda x, y: inner(x, y) + (255,), alpha=True)

        result = self.compare(render)

        self.assertIn("alpha channel", result.stderr)

    def test_missing_input_is_a_usage_error(self) -> None:
        result = self.compare(self.root / "absent.png")

        self.assertEqual(result.returncode, 2)
        self.assertIn("render not found", result.stderr)

    def test_non_png_input_is_a_usage_error(self) -> None:
        broken = self.root / "broken.png"
        broken.write_bytes(b"not a png at all")

        result = self.compare(broken)

        self.assertEqual(result.returncode, 2)
        self.assertIn("not a PNG", result.stderr)

    def test_bad_grid_is_a_usage_error(self) -> None:
        result = self.compare(self.render, "--grid", "12")

        self.assertEqual(result.returncode, 2)
        self.assertIn("COLSxROWS", result.stderr)


class TestBatch(ScreenshotDiffTestCase):
    def test_batch_runs_every_pair_and_fails_if_any_pair_fails(self) -> None:
        width, height = RENDER_SIZE
        inner = scaled_box(width, height, 0.22, 0.78, 0.23, 0.74)
        broken = self.render_with(
            "broken.png",
            lambda x, y: BAR if (x < width * 0.09 or x > width * 0.91) else inner(x, y),
        )

        plan = self.root / "plan.json"
        plan.write_text(
            json.dumps(
                [
                    {"label": "Onboarding/iPhone 15", "render": self.render.name, "mock": self.mock.name},
                    {"label": "Onboarding/iPhone SE", "render": broken.name, "mock": self.mock.name},
                ]
            ),
            encoding="utf-8",
        )

        result = run("batch", "--plan", str(plan), "--relative-to-plan")

        self.assertEqual(result.returncode, 1)
        self.assertIn("PASS  Onboarding/iPhone 15", result.stdout)
        self.assertIn("FAIL  Onboarding/iPhone SE", result.stdout)
        self.assertIn("2 pairs, 1 failed", result.stdout)

    def test_plan_entry_without_paths_is_a_usage_error(self) -> None:
        plan = self.root / "plan.json"
        plan.write_text(json.dumps([{"label": "no paths"}]), encoding="utf-8")

        result = run("batch", "--plan", str(plan), "--relative-to-plan")

        self.assertEqual(result.returncode, 2)
        self.assertIn("needs `render` and `mock`", result.stderr)

    def test_per_entry_ignore_bands_override_the_defaults(self) -> None:
        width, height = RENDER_SIZE
        inner = scaled_box(width, height, 0.13, 0.87, 0.23, 0.74)
        with_bar = self.render_with(
            "statusbar.png", lambda x, y: (0, 0, 0) if y < height * 0.05 else inner(x, y)
        )

        plan = self.root / "plan.json"
        plan.write_text(
            json.dumps([{"label": "SE", "render": with_bar.name, "mock": self.mock.name, "ignore_top": "6%"}]),
            encoding="utf-8",
        )

        result = run("batch", "--plan", str(plan), "--relative-to-plan")

        self.assertEqual(result.returncode, 0, result.stdout)


if __name__ == "__main__":
    unittest.main()
