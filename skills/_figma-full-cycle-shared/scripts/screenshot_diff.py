#!/usr/bin/env python3
"""Compare an implementation screenshot against a design mock, without looking.

Stages 5 and 6 confirm per screen and per device that the layout fits, that
there is no unintended letterboxing, that content is not clipped and that the
background reaches the edges. Done by eye that is one image into the model's
context per row — a 5-screen feature with a 6-row matrix costs more context
than the whole skill.

This answers the mechanical part in about 0.4s per pair and returns a verdict,
so the model looks at the rows that failed instead of at every row.

It compares images of DIFFERENT sizes on purpose: the mock is normalized to the
render's dimensions first. Comparing only at the reference size is what hides a
fixed-canvas layout, which is the defect stage 5 exists to catch.

Deliberately partial, and it says so with every run: it sees geometry, not
meaning. A wrong typeface, a mirrored icon, a shade under the threshold or
wrong copy all pass. The gate is this script plus eyes on what it flags — never
this script alone.

Across device classes it says less, on purpose. Normalizing stretches the mock
anisotropically, while a native layout adapts by holding its metrics in points,
so the structural grid diff reports a large difference for a correctly adapted
screen and cannot tell that apart from broken scaling. Beyond `--aspect-
tolerance` the grid and the bottom-band count are therefore reported but not
gated, and the verdict rests on letterbox, pillarbox and background-to-the-edge
— the checks that survive a change of aspect. Clipping on a smaller device
stays a reviewer question, which is why stage 6 requires eyes on that row.

Requires `sips` (every macOS since 10.4). The pipeline already requires macOS
for `xcrun simctl`, so this adds no new dependency, and nothing to pip install.
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


SRGB_PROFILE = "/System/Library/ColorSync/Profiles/sRGB Profile.icc"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
ALPHA_COLOR_TYPES = {4, 6}

# What a "same colour" and a "real difference" mean, in 0-255 max-channel
# distance. Defaults are tuned to pass an sRGB/Display-P3 round trip (~10-15 on
# saturated colours) while still catching a structural break.
DEFAULT_BAND_TOLERANCE = 10
DEFAULT_BAND_MISMATCH = 30
DEFAULT_MIN_BAND_PX = 8
DEFAULT_CORNER_THRESHOLD = 30
DEFAULT_CELL_THRESHOLD = 25
DEFAULT_BAD_RATIO = 0.05
DEFAULT_GRID = (12, 24)
DEFAULT_SAMPLE_STEP = 3
LINE_SAMPLES = 48
# Beyond this relative difference in aspect ratio the grid stops being able to
# separate a correctly adapted layout from a badly scaled one. 2% keeps the
# ordinary retina-scale mismatch comparable and drops device-class changes.
DEFAULT_ASPECT_TOLERANCE = 0.02

BLIND_TO = (
    "typeface, weight and letter spacing",
    "a colour difference below the cell threshold",
    "text content, truncation and translation",
    "icon shape, and a mirrored or wrong glyph",
    "anything inside an ignored band",
)


EPILOG = """Exit codes: 0 every pair passed, 1 at least one failed, 2 usage error.
The last stdout line is SCREENSHOT_DIFF_CLEAN or SCREENSHOT_DIFF_DIRTY — those two values,
nothing else, safe to grep.

The verdict gates on letterbox, pillarbox and background-to-the-edge. When the mock and the
render differ in aspect ratio by more than --aspect-tolerance, the grid diff and the
bottom-band count are reported but NOT gated: a correctly adapted native layout diverges from
the stretched mock exactly as a broken one does. Clipping on a smaller device is a reviewer
question, not a verdict.

Use --grid-map to see where the cells differ, and --out to keep the full JSON report on disk.
"""


class DiffError(RuntimeError):
    pass


@dataclass
class Image:
    width: int
    height: int
    data: bytes
    offset: int
    stride: int
    bytes_per_pixel: int
    top_down: bool

    def pixel(self, x: int, y: int) -> Tuple[int, int, int]:
        row = y if self.top_down else self.height - 1 - y
        start = self.offset + row * self.stride + x * self.bytes_per_pixel
        return (self.data[start + 2], self.data[start + 1], self.data[start])


@dataclass
class Options:
    band_tolerance: int = DEFAULT_BAND_TOLERANCE
    band_mismatch: int = DEFAULT_BAND_MISMATCH
    min_band_px: int = DEFAULT_MIN_BAND_PX
    corner_threshold: int = DEFAULT_CORNER_THRESHOLD
    cell_threshold: int = DEFAULT_CELL_THRESHOLD
    bad_ratio: float = DEFAULT_BAD_RATIO
    grid: Tuple[int, int] = DEFAULT_GRID
    sample_step: int = DEFAULT_SAMPLE_STEP
    aspect_tolerance: float = DEFAULT_ASPECT_TOLERANCE
    ignore_top: str = "0"
    ignore_bottom: str = "0"
    match_profile: bool = True
    label: str = ""
    notes: List[str] = field(default_factory=list)


# --------------------------------------------------------------------------
# Input
# --------------------------------------------------------------------------


def png_header(path: Path) -> Tuple[int, int, int]:
    """(width, height, colour_type) straight out of IHDR."""
    with path.open("rb") as handle:
        head = handle.read(26)
    if len(head) < 26 or not head.startswith(PNG_MAGIC):
        raise DiffError("not a PNG: {}".format(path))
    width, height = struct.unpack_from(">II", head, 16)
    colour_type = head[25]
    return width, height, colour_type


def run_sips(args: Sequence[str]) -> None:
    result = subprocess.run(["sips", *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise DiffError("sips failed: {}".format(result.stderr.strip() or " ".join(args)))


def to_bmp(source: Path, out_dir: Path, size: Optional[Tuple[int, int]], match_profile: bool) -> Path:
    out = out_dir / (source.name + ".bmp")
    args: List[str] = []
    if match_profile and os.path.exists(SRGB_PROFILE):
        args += ["--matchTo", SRGB_PROFILE]
    if size is not None:
        # sips -z takes height then width.
        args += ["-z", str(size[1]), str(size[0])]
    args += ["-s", "format", "bmp", str(source), "--out", str(out)]
    run_sips(args)
    return out


def read_bmp(path: Path) -> Image:
    data = path.read_bytes()
    if len(data) < 54 or data[:2] != b"BM":
        raise DiffError("not a BMP: {}".format(path))
    offset = struct.unpack_from("<I", data, 10)[0]
    width, signed_height = struct.unpack_from("<ii", data, 18)
    bits = struct.unpack_from("<H", data, 28)[0]
    if bits not in (24, 32):
        raise DiffError("unsupported BMP depth {} in {}".format(bits, path))
    bytes_per_pixel = bits // 8
    # A negative height means the rows are stored top-down. Current macOS sips
    # writes exactly that; older ones write bottom-up. Both are valid BMP.
    top_down = signed_height < 0
    height = abs(signed_height)
    stride = (width * bytes_per_pixel + 3) & ~3
    if offset + stride * height > len(data):
        raise DiffError("truncated BMP: {}".format(path))
    return Image(width, height, data, offset, stride, bytes_per_pixel, top_down)


def parse_extent(value: str, total: int) -> int:
    """`120` → 120 px; `5%` → 5% of `total`."""
    text = value.strip()
    if not text:
        return 0
    try:
        if text.endswith("%"):
            return max(0, min(total, round(total * float(text[:-1]) / 100.0)))
        return max(0, min(total, int(round(float(text)))))
    except ValueError:
        raise DiffError("expected a number or a percentage, got {!r}".format(value))


def parse_grid(value: str) -> Tuple[int, int]:
    parts = value.lower().split("x")
    if len(parts) != 2:
        raise DiffError("--grid expects COLSxROWS, e.g. 12x24")
    try:
        cols, rows = int(parts[0]), int(parts[1])
    except ValueError:
        raise DiffError("--grid expects COLSxROWS, e.g. 12x24")
    if cols < 1 or rows < 1:
        raise DiffError("--grid needs positive dimensions")
    return cols, rows


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------


def distance(left: Tuple[int, int, int], right: Tuple[int, int, int]) -> int:
    return max(abs(left[0] - right[0]), abs(left[1] - right[1]), abs(left[2] - right[2]))


def uniform_line(
    image: Image, index: int, vertical: bool, top: int, bottom: int, tolerance: int
) -> Optional[Tuple[int, int, int]]:
    """The colour of a fully uniform column/row, or None.

    Sampled at a fixed count rather than a fixed stride: a band worth finding is
    uniform along its whole length, so extra samples buy nothing, while a fixed
    stride makes a tall retina screenshot pay per pixel.
    """
    span = (bottom - top) if vertical else image.width
    if span <= 0:
        return None
    step = max(1, span // min(LINE_SAMPLES, span))
    if vertical:
        colours = [image.pixel(index, y) for y in range(top, bottom, step)]
    else:
        colours = [image.pixel(x, index) for x in range(0, image.width, step)]
    if not colours:
        return None
    base = colours[0]
    return base if all(distance(colour, base) <= tolerance for colour in colours) else None


def edge_band(image: Image, side: str, top: int, bottom: int, tolerance: int) -> Tuple[int, Optional[Tuple[int, int, int]]]:
    """Width of the uniform full-length band at an edge, and its colour."""
    span = image.width if side in ("left", "right") else bottom - top
    limit = max(1, span // 3)
    colour: Optional[Tuple[int, int, int]] = None
    width = 0
    for step in range(limit):
        if side == "left":
            found = uniform_line(image, step, True, top, bottom, tolerance)
        elif side == "right":
            found = uniform_line(image, image.width - 1 - step, True, top, bottom, tolerance)
        elif side == "top":
            found = uniform_line(image, top + step, False, top, bottom, tolerance)
        else:
            found = uniform_line(image, bottom - 1 - step, False, top, bottom, tolerance)
        if found is None or (colour is not None and distance(found, colour) > tolerance):
            break
        colour = colour or found
        width += 1
    return width, colour


def cell_means(
    image: Image, top: int, bottom: int, cols: int, rows: int, step: int
) -> List[Tuple[int, int, int]]:
    means: List[Tuple[int, int, int]] = []
    height = bottom - top
    for row in range(rows):
        y0 = top + height * row // rows
        y1 = top + height * (row + 1) // rows
        for col in range(cols):
            x0 = image.width * col // cols
            x1 = image.width * (col + 1) // cols
            total_r = total_g = total_b = count = 0
            for y in range(y0, max(y0 + 1, y1), step):
                for x in range(x0, max(x0 + 1, x1), step):
                    red, green, blue = image.pixel(x, y)
                    total_r += red
                    total_g += green
                    total_b += blue
                    count += 1
            if count == 0:
                means.append((0, 0, 0))
            else:
                means.append((total_r // count, total_g // count, total_b // count))
    return means


def aspect_of(size: Tuple[int, int]) -> float:
    width, height = size
    return float(height) / float(width) if width else 0.0


def grid_map(cols: int, rows: int, bad: Sequence[Dict[str, object]]) -> List[str]:
    """Where the cells differ, as text.

    `44% of cells differ` does not say whether the screen shifted, lost its
    bottom, or drifted on one side — and finding out otherwise means opening the
    images, which is the cost this script exists to avoid.
    """
    flagged = {(int(cell["col"]), int(cell["row"])) for cell in bad}
    return [
        "".join("#" if (col, row) in flagged else "." for col in range(cols)) for row in range(rows)
    ]


def compare_images(
    render: Image,
    mock: Image,
    options: Options,
    render_size: Tuple[int, int],
    mock_size: Tuple[int, int],
) -> Dict[str, object]:
    if (render.width, render.height) != (mock.width, mock.height):
        raise DiffError("normalization failed: render and mock differ after resize")

    ignore_top = parse_extent(options.ignore_top, render.height)
    ignore_bottom = parse_extent(options.ignore_bottom, render.height)
    top = ignore_top
    bottom = render.height - ignore_bottom
    if bottom - top < 8:
        raise DiffError("ignored bands leave nothing to compare")

    # Normalizing the mock to the render's size stretches it anisotropically
    # when the aspects differ. A native layout adapts by keeping its metrics in
    # points, not by scaling, so its content lands somewhere else than the
    # stretched mock's — and the grid then reports a large difference for a
    # correctly adapted screen. It cannot tell that apart from broken scaling,
    # so across aspects the grid is reported and not gated on.
    render_aspect = aspect_of(render_size)
    mock_aspect = aspect_of(mock_size)
    aspect_delta = abs(render_aspect - mock_aspect) / render_aspect if render_aspect else 0.0
    grid_comparable = aspect_delta <= options.aspect_tolerance

    report: Dict[str, object] = {
        "size": [render.width, render.height],
        "compared_rows": [top, bottom],
        "aspect": {
            "render": round(render_aspect, 3),
            "mock": round(mock_aspect, 3),
            "delta": round(aspect_delta, 3),
            "grid_comparable": grid_comparable,
        },
        "checks": {},
    }

    bands: Dict[str, object] = {}
    for side in ("left", "right", "top", "bottom"):
        render_width, render_colour = edge_band(render, side, top, bottom, options.band_tolerance)
        mock_width, mock_colour = edge_band(mock, side, top, bottom, options.band_tolerance)
        suspect = render_width >= options.min_band_px and (
            mock_width < options.min_band_px
            or (
                render_colour is not None
                and mock_colour is not None
                and distance(render_colour, mock_colour) > options.band_mismatch
            )
        )
        bands[side] = {
            "render_band_px": render_width,
            "mock_band_px": mock_width,
            "render_color": render_colour,
            "mock_color": mock_colour,
            "suspect": suspect,
        }
    report["checks"]["edge_bands"] = bands

    letterbox = bool(bands["top"]["suspect"] and bands["bottom"]["suspect"])
    pillarbox = bool(bands["left"]["suspect"] and bands["right"]["suspect"])

    corners: Dict[str, object] = {}
    positions = {
        "tl": (2, top + 2),
        "tr": (render.width - 3, top + 2),
        "bl": (2, bottom - 3),
        "br": (render.width - 3, bottom - 3),
    }
    for name, (x, y) in positions.items():
        render_pixel = render.pixel(x, y)
        mock_pixel = mock.pixel(x, y)
        delta = distance(render_pixel, mock_pixel)
        corners[name] = {
            "render": list(render_pixel),
            "mock": list(mock_pixel),
            "delta": delta,
            "ok": delta <= options.corner_threshold,
        }
    report["checks"]["corners"] = corners

    cols, rows = options.grid
    render_cells = cell_means(render, top, bottom, cols, rows, options.sample_step)
    mock_cells = cell_means(mock, top, bottom, cols, rows, options.sample_step)
    bad = []
    for index, (left, right) in enumerate(zip(render_cells, mock_cells)):
        delta = distance(left, right)
        if delta > options.cell_threshold:
            bad.append({"col": index % cols, "row": index // cols, "delta": delta})
    ratio = round(len(bad) / float(cols * rows), 3)
    report["checks"]["grid"] = {
        "cols": cols,
        "rows": rows,
        "bad_cells": bad,
        "bad_ratio": ratio,
        "comparable": grid_comparable,
        "map": grid_map(cols, rows, bad),
    }

    bottom_band_rows = max(1, rows // 6)
    bottom_area_bad = sum(1 for cell in bad if cell["row"] >= rows - bottom_band_rows)
    background_ok = all(corner["ok"] for corner in corners.values())

    structural_ok = not letterbox and not pillarbox and background_ok
    passes = structural_ok and (not grid_comparable or ratio < options.bad_ratio)

    report["verdict"] = {
        "label": options.label,
        "letterbox": letterbox,
        "pillarbox": pillarbox,
        "bg_reaches_edges": background_ok,
        "bottom_area_diff_cells": bottom_area_bad,
        "grid_bad_ratio": ratio,
        "grid_comparable": grid_comparable,
        "pass": passes,
    }
    return report


# --------------------------------------------------------------------------
# Driving
# --------------------------------------------------------------------------


def analyze(render_path: Path, mock_path: Path, options: Options) -> Dict[str, object]:
    started = time.time()
    notes = list(options.notes)

    sizes: Dict[str, Tuple[int, int]] = {}
    for role, path in (("render", render_path), ("mock", mock_path)):
        if not path.is_file():
            raise DiffError("{} not found: {}".format(role, path))
        width, height, colour_type = png_header(path)
        sizes[role] = (width, height)
        if colour_type in ALPHA_COLOR_TYPES:
            # A simulator capture routinely carries alpha and there is nothing to
            # re-export; only the mock's transparency is the author's to fix.
            remedy = (
                "export the frame without transparency"
                if role == "mock"
                else "expected for a simulator capture; only the edges are affected"
            )
            notes.append(
                "{} has an alpha channel; sips flattens it and the edges may differ — {}".format(
                    role, remedy
                )
            )

    with tempfile.TemporaryDirectory() as raw_dir:
        temp = Path(raw_dir)
        render_bmp = to_bmp(render_path, temp, None, options.match_profile)
        render = read_bmp(render_bmp)
        mock_bmp = to_bmp(mock_path, temp, (render.width, render.height), options.match_profile)
        mock = read_bmp(mock_bmp)
        report = compare_images(render, mock, options, sizes["render"], sizes["mock"])

    report["render"] = str(render_path)
    report["mock"] = str(mock_path)
    report["notes"] = notes
    report["blind_to"] = list(BLIND_TO)
    report["elapsed_s"] = round(time.time() - started, 2)
    return report


def options_from_args(args: argparse.Namespace) -> Options:
    return Options(
        band_tolerance=args.band_tolerance,
        band_mismatch=args.band_mismatch,
        min_band_px=args.min_band_px,
        corner_threshold=args.corner_threshold,
        cell_threshold=args.cell_threshold,
        bad_ratio=args.bad_ratio,
        grid=parse_grid(args.grid),
        sample_step=args.sample_step,
        aspect_tolerance=args.aspect_tolerance,
        ignore_top=args.ignore_top,
        ignore_bottom=args.ignore_bottom,
        match_profile=not args.no_color_match,
    )


def emit(reports: Sequence[Dict[str, object]], args: argparse.Namespace) -> int:
    failed = [report for report in reports if not report["verdict"]["pass"]]

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(reports, indent=2, sort_keys=True), encoding="utf-8")

    if args.format == "json":
        print(json.dumps([report["verdict"] for report in reports], sort_keys=True))
    else:
        for report in reports:
            verdict = report["verdict"]
            aspect = report.get("aspect", {})
            label = verdict["label"] or Path(str(report["render"])).name
            grid_note = "grid {:.1%}".format(verdict["grid_bad_ratio"])
            if not verdict.get("grid_comparable", True):
                grid_note += " (not gated: mock {} vs render {} aspect)".format(
                    aspect.get("mock"), aspect.get("render")
                )

            if verdict["pass"]:
                print("PASS  {}  {}".format(label, grid_note))
                if not verdict.get("grid_comparable", True):
                    # A bare PASS reads as "all good", and here it does not mean
                    # that: clipping was measured and deliberately not judged.
                    print("      bottom band not gated — check content clipping by eye")
                continue

            reasons = []
            for side in ("left", "right", "top", "bottom"):
                band = report["checks"]["edge_bands"][side]
                if band["suspect"]:
                    reasons.append("{} band {}px".format(side, band["render_band_px"]))
            if verdict["letterbox"]:
                reasons.append("letterbox")
            if verdict["pillarbox"]:
                reasons.append("pillarbox")
            if not verdict["bg_reaches_edges"]:
                reasons.append("background stops before the edge")
            if verdict.get("grid_comparable", True):
                if verdict["bottom_area_diff_cells"]:
                    reasons.append(
                        "{} cells differ in the bottom band".format(verdict["bottom_area_diff_cells"])
                    )
                if verdict["grid_bad_ratio"] >= args.bad_ratio:
                    reasons.append("grid {:.1%} over threshold".format(verdict["grid_bad_ratio"]))
            print("FAIL  {}  {}".format(label, "; ".join(reasons) or "verdict false"))
            if not verdict.get("grid_comparable", True):
                print("      {}".format(grid_note))

        if args.grid_map:
            for report in reports:
                verdict = report["verdict"]
                label = verdict["label"] or Path(str(report["render"])).name
                grid = report["checks"]["grid"]
                print("\n{}  grid {}x{}  (. match, # differs)".format(label, grid["cols"], grid["rows"]))
                for row in grid["map"]:
                    print("  {}".format(row))

        for report in reports:
            for note in report.get("notes", []):
                print("note: {}".format(note), file=sys.stderr)

        print("\nBlind to: {}.".format("; ".join(BLIND_TO)))
        print("Look at every FAIL, and at one PASS per screen — geometry matching is not the design matching.")
        if args.out:
            print("Full report: {}".format(args.out))
        print(
            "screenshot-diff: {} pair{}, {} failed".format(
                len(reports), "" if len(reports) == 1 else "s", len(failed)
            )
        )
        print("SCREENSHOT_DIFF_DIRTY" if failed else "SCREENSHOT_DIFF_CLEAN")

    return 1 if failed else 0


def run_compare(args: argparse.Namespace) -> int:
    options = options_from_args(args)
    options.label = args.label or ""
    report = analyze(Path(args.render), Path(args.mock), options)
    return emit([report], args)


def run_batch(args: argparse.Namespace) -> int:
    plan_path = Path(args.plan)
    if not plan_path.is_file():
        raise DiffError("plan not found: {}".format(plan_path))
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except ValueError as error:
        raise DiffError("plan is not valid JSON: {}".format(error))
    if not isinstance(plan, list) or not plan:
        raise DiffError("plan must be a non-empty list of {label, render, mock} objects")

    base = plan_path.parent if args.relative_to_plan else Path(args.project_root)
    reports: List[Dict[str, object]] = []
    for index, entry in enumerate(plan):
        if not isinstance(entry, dict) or "render" not in entry or "mock" not in entry:
            raise DiffError("plan entry {} needs `render` and `mock`".format(index))
        options = options_from_args(args)
        options.label = str(entry.get("label", "")) or ""
        for key in ("ignore_top", "ignore_bottom"):
            if key in entry:
                setattr(options, key, str(entry[key]))
        reports.append(
            analyze(base / str(entry["render"]), base / str(entry["mock"]), options)
        )
    return emit(reports, args)


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--out", help="Write the full JSON report here; stdout keeps the verdict only")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument(
        "--ignore-top",
        default="0",
        help="Band to exclude from the top, px or %% of height (status bar)",
    )
    parser.add_argument(
        "--ignore-bottom",
        default="0",
        help="Band to exclude from the bottom, px or %% of height (home indicator)",
    )
    parser.add_argument("--grid", default="12x24", help="Grid for the coarse diff (default 12x24)")
    parser.add_argument("--cell-threshold", type=int, default=DEFAULT_CELL_THRESHOLD)
    parser.add_argument("--bad-ratio", type=float, default=DEFAULT_BAD_RATIO)
    parser.add_argument("--corner-threshold", type=int, default=DEFAULT_CORNER_THRESHOLD)
    parser.add_argument("--band-tolerance", type=int, default=DEFAULT_BAND_TOLERANCE)
    parser.add_argument("--band-mismatch", type=int, default=DEFAULT_BAND_MISMATCH)
    parser.add_argument("--min-band-px", type=int, default=DEFAULT_MIN_BAND_PX)
    parser.add_argument("--sample-step", type=int, default=DEFAULT_SAMPLE_STEP)
    parser.add_argument(
        "--grid-map",
        action="store_true",
        help="Print which cells differ as a text map — where the difference is, not just how much",
    )
    parser.add_argument(
        "--aspect-tolerance",
        type=float,
        default=DEFAULT_ASPECT_TOLERANCE,
        help=(
            "Relative aspect-ratio difference above which the grid diff is reported but not "
            "gated on, because it cannot tell a correctly adapted layout from a badly scaled "
            "one (default %(default)s)"
        ),
    )
    parser.add_argument(
        "--no-color-match",
        action="store_true",
        help="Skip the sRGB conversion (default converts both inputs with sips --matchTo)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare implementation screenshots against design mocks of any size.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    compare = subparsers.add_parser(
        "compare",
        help="Compare one render against one mock",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    compare.add_argument("--render", required=True)
    compare.add_argument("--mock", required=True)
    compare.add_argument("--label", help="Name for this pair in the output")
    add_common(compare)
    compare.set_defaults(handler=run_compare)

    batch = subparsers.add_parser(
        "batch",
        help="Compare every pair in a JSON plan (the stage 6 matrix)",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    batch.add_argument("--plan", required=True, help="JSON list of {label, render, mock} objects")
    batch.add_argument("--project-root", default=".")
    batch.add_argument(
        "--relative-to-plan",
        action="store_true",
        help="Resolve paths against the plan file instead of --project-root",
    )
    add_common(batch)
    batch.set_defaults(handler=run_batch)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.handler(args)
    except DiffError as error:
        print("error: {}".format(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
