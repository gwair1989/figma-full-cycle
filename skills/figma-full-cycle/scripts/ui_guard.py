#!/usr/bin/env python3
"""Detect Layout and Colors contract violations in a feature's changed files.

The Layout and Colors contracts state their rules as grep detections. Left as
prose, every run re-derives the patterns, reads the diff by hand, and pays for
both in context — and a pattern that misses one literal form reports a clean
run while that form spreads (colors-contract.md FAIL-02).

This script owns the mechanical half. It reports `path:line: RULE-ID: message`
and nothing else, so the model reads findings instead of source.

Deliberately partial, and it says so: rules that need project knowledge or a
screenshot cannot be regex-checked, and a clean run is only as wide as the
coverage note printed with it. Swift is parsed by pattern, not by grammar.

Waive a finding in code with a comment on the line or the line above:

    // ui-guard: allow LAY-04 — animated entrance, restored on completion
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


MAX_FILE_BYTES = 2_000_000
SWIFT_SUFFIXES = (".swift",)

# Rules this script actually checks. Everything else in the contracts is left
# to the reviewer, and named in the coverage note so a clean run is not read
# as more than it is.
CHECKED = {
    "LAY-01": "fixed reference canvas scaled as a whole",
    "LAY-02": "hard frame on Color/Rectangle/RoundedRectangle",
    "LAY-03": "hard or derived screen-level sizes",
    "LAY-04": "position / static offset used as layout",
    "LAY-08": "background applied before the stretch frame",
    "LAY-09": "scaleEffect on a text-bearing container",
    "LAY-10": "geometry arithmetic without a derivation",
    "COL-01": "palette symbol referenced outside the semantic layer",
    "COL-02": "two palette entries with the same value",
    "COL-04": "alpha encoded in a palette entry name",
    "COL-05": "inline color literal",
}

UNCHECKED = {
    "LAY-05": "position with alignment, space with padding — needs intent",
    "LAY-06": "flexible frame initializers first — needs intent",
    "LAY-07": "inset snapping — needs the project's system values",
    "LAY-11": "adaptivity evidence — stage 6 screenshots, not source",
    "COL-03": "one naming scheme for the palette — a project decision",
    "COL-06": "values taken from design context — needs the Figma value",
    "COL-07": "appearance variants preserved — needs the variant pair",
    "COL-08": "system and brand slots stay slots — needs the project's slots",
    "COL-09": "a missing token is a question — needs the token inventory",
}

WAIVER_RE = re.compile(r"//\s*ui-guard:\s*allow\s+([A-Z]{3}-\d{2})")
STRING_RE = re.compile(r'"(?:\\.|[^"\\])*"')
HEX_STRING_RE = re.compile(r'"\s*#?[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?\s*"')
ARITHMETIC_RE = re.compile(r"[\w.)\]]\s*[-+*/]\s*[\w.(]")
GREEDY_SHAPE_RE = re.compile(r"\b(Color|Rectangle|RoundedRectangle|Capsule|Circle|Ellipse)\b")
GEOMETRY_RE = re.compile(r"\b(safeAreaInsets|geo\.size|proxy\.size|geometry\.size|UIScreen\.main\.bounds)\b")
ANIMATION_RE = re.compile(
    r"\b(withAnimation|matchedGeometryEffect|transition|animation|Animation|"
    r"isAnimating|animate|GestureState|DragGesture|offsetY|dragOffset)\b"
)
PREVIEW_RE = re.compile(r"#Preview\b|\bPreviewProvider\b|\bPreviewLayout\b")

# COL-05 must enumerate every form. A detection that covers two of them and
# misses the third is the failure this rule exists to prevent.
COLOR_LITERAL_PATTERNS: Sequence[Tuple[re.Pattern, str]] = (
    (re.compile(r"#colorLiteral\s*\("), "#colorLiteral"),
    (re.compile(r"\bColor\s*\(\s*red\s*:"), "Color(red:)"),
    (re.compile(r"\bColor\s*\(\s*white\s*:"), "Color(white:)"),
    (re.compile(r"\bColor\s*\(\s*hue\s*:"), "Color(hue:)"),
    (re.compile(r"\bColor\s*\(\s*(?:\w+\s*:\s*)?hex\b|\bColor\s*\(\s*hex\s*:"), "Color(hex:)"),
    (re.compile(r"\bUIColor\s*\(\s*red\s*:"), "UIColor(red:)"),
    (re.compile(r"\bUIColor\s*\(\s*white\s*:"), "UIColor(white:)"),
    (re.compile(r"\bUIColor\s*\(\s*hue\s*:"), "UIColor(hue:)"),
    (re.compile(r"\bUIColor\s*\(\s*displayP3Red\s*:"), "UIColor(displayP3Red:)"),
    (re.compile(r"\bNSColor\s*\(\s*(?:red|white|hue|calibratedRed|deviceRed|displayP3Red)\s*:"), "NSColor(...)"),
    (re.compile(r"\bCGColor\s*\(\s*(?:red|gray|components)\s*:"), "CGColor(...)"),
)

ALPHA_NAME_RE = re.compile(
    r"(?:alpha|opacity)[-_]?\d{1,3}$|[-_]\d{1,3}(?:pct|percent)$|\d{1,3}%$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    rule: str
    message: str
    context: str = ""
    waived: bool = False

    def render(self) -> str:
        suffix = ""
        if self.context:
            suffix += " [{}]".format(self.context)
        if self.waived:
            suffix += " [waived]"
        return "{}:{}: {}: {}{}".format(self.path, self.line, self.rule, self.message, suffix)

    def as_dict(self) -> Dict[str, object]:
        return {
            "path": self.path,
            "line": self.line,
            "rule": self.rule,
            "message": self.message,
            "context": self.context,
            "waived": self.waived,
        }


@dataclass
class Chain:
    """Consecutive lines forming one modifier chain, joined for matching."""

    start_line: int
    line_numbers: List[int]
    text: str


class SourceFile:
    """A Swift file with strings and comments blanked out for matching."""

    def __init__(self, path: Path, display: str) -> None:
        self.path = path
        self.display = display
        raw = path.read_text(encoding="utf-8", errors="replace")
        self.raw_lines = raw.splitlines()
        self.code_lines = [strip_noncode(line) for line in self.raw_lines]
        self.string_lines = [STRING_RE.findall(line) for line in self.raw_lines]
        self.chains = build_chains(self.code_lines)
        self.preview_lines = preview_regions(self.raw_lines)

    def has_text_views(self) -> bool:
        return any(re.search(r"\bText\s*\(", line) for line in self.code_lines)


def strip_noncode(line: str) -> str:
    """Blank string literals, then drop a trailing line comment."""
    blanked = STRING_RE.sub('""', line)
    marker = blanked.find("//")
    if marker != -1:
        blanked = blanked[:marker]
    return blanked


def build_chains(code_lines: Sequence[str]) -> List[Chain]:
    """Join a line with the continuation lines that start with a dot."""
    chains: List[Chain] = []
    index = 0
    total = len(code_lines)
    while index < total:
        if not code_lines[index].strip():
            index += 1
            continue
        numbers = [index + 1]
        parts = [code_lines[index].strip()]
        cursor = index + 1
        while cursor < total and code_lines[cursor].lstrip().startswith("."):
            numbers.append(cursor + 1)
            parts.append(code_lines[cursor].strip())
            cursor += 1
        chains.append(Chain(start_line=index + 1, line_numbers=numbers, text=" ".join(parts)))
        index = cursor if cursor > index + 1 else index + 1
    return chains


def preview_regions(raw_lines: Sequence[str]) -> set:
    """Line numbers that sit inside a #Preview or PreviewProvider block."""
    inside: set = set()
    depth = 0
    active = False
    for number, line in enumerate(raw_lines, start=1):
        if not active:
            if not PREVIEW_RE.search(line):
                continue
            active = True
            depth = 0
        inside.add(number)
        opened = line.count("{")
        closed = line.count("}")
        depth += opened - closed
        if depth <= 0 and (opened or closed):
            active = False
            depth = 0
    return inside


def balanced_args(text: str, start: int) -> str:
    """Return the argument text of a call whose '(' sits at `start`."""
    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return text[start + 1 : index]
    return text[start + 1 :]


def frame_calls(text: str) -> Iterable[str]:
    for match in re.finditer(r"\.frame\s*\(", text):
        yield balanced_args(text, match.end() - 1)


def labelled_value(args: str, label: str) -> Optional[str]:
    match = re.search(r"(?<![\w.]){}\s*:".format(label), args)
    if not match:
        return None
    rest = args[match.end() :]
    depth = 0
    for index, char in enumerate(rest):
        if char in "([":
            depth += 1
        elif char in ")]":
            depth -= 1
        elif char == "," and depth == 0:
            return rest[:index].strip()
    return rest.strip()


def numeric(value: str) -> Optional[float]:
    stripped = value.strip()
    try:
        return float(stripped)
    except ValueError:
        return None


# --------------------------------------------------------------------------
# Layout rules
# --------------------------------------------------------------------------


def check_layout(source: SourceFile, canvas: Optional[Tuple[float, float]]) -> List[Finding]:
    findings: List[Finding] = []
    canvas_sizes = set(canvas) if canvas else set()

    file_has_scale_effect = any(".scaleEffect(" in line for line in source.code_lines)
    file_has_canvas_frame = False

    for chain in source.chains:
        text = chain.text
        line = chain.start_line

        for args in frame_calls(text):
            width = labelled_value(args, "width")
            height = labelled_value(args, "height")

            for label, value in (("width", width), ("height", height)):
                if value is None:
                    continue
                number = numeric(value)

                if number is not None and (number in canvas_sizes or (not canvas_sizes and number >= 300)):
                    file_has_canvas_frame = True

                if number is None and ARITHMETIC_RE.search(value):
                    findings.append(
                        Finding(
                            source.display,
                            line,
                            "LAY-03",
                            "arithmetic inside .frame({}: {}) — an inset is padding, not a subtraction".format(
                                label, value.strip()
                            ),
                        )
                    )
                elif number is not None and number >= 300:
                    findings.append(
                        Finding(
                            source.display,
                            line,
                            "LAY-03",
                            "screen-level .frame({}: {:g}) — stretch with maxWidth/maxHeight instead".format(
                                label, number
                            ),
                        )
                    )

                if number is not None and GREEDY_SHAPE_RE.match(text.strip()):
                    findings.append(
                        Finding(
                            source.display,
                            line,
                            "LAY-02",
                            "hard .frame({}: {:g}) on a greedy shape — the frame shrinks it".format(label, number),
                        )
                    )

        position = re.search(r"\.position\s*\(", text)
        if position:
            findings.append(
                Finding(
                    source.display,
                    line,
                    "LAY-04",
                    ".position(...) is not a layout mechanism — position with alignment, space with padding",
                )
            )

        offset = re.search(r"\.offset\s*\(", text)
        if offset and not ANIMATION_RE.search(text):
            args = balanced_args(text, offset.end() - 1)
            values = [labelled_value(args, "x"), labelled_value(args, "y")]
            static = [value for value in values if value is not None and numeric(value) is not None]
            if static:
                findings.append(
                    Finding(
                        source.display,
                        line,
                        "LAY-04",
                        "static .offset({}) used as layout — allowed only for animation, with the reason recorded".format(
                            args.strip()
                        ),
                    )
                )

        background = text.find(".background(")
        stretch = re.search(r"\.frame\s*\([^)]*max(?:Width|Height)\s*:\s*\.infinity", text)
        if background != -1 and stretch and background < stretch.start():
            findings.append(
                Finding(
                    source.display,
                    line,
                    "LAY-08",
                    ".background(...) before the stretch frame — it paints the content size, not the screen",
                )
            )

        if ".scaleEffect(" in text and source.has_text_views():
            findings.append(
                Finding(
                    source.display,
                    line,
                    "LAY-09",
                    "scaleEffect in a file with Text — rasterized scaling disables re-layout and Dynamic Type",
                )
            )

    if file_has_scale_effect and file_has_canvas_frame:
        line = next(
            (number for number, text in enumerate(source.code_lines, start=1) if ".scaleEffect(" in text),
            1,
        )
        findings.append(
            Finding(
                source.display,
                line,
                "LAY-01",
                "fixed canvas frame plus scaleEffect — an aspect-fit of the artboard, not adaptation",
            )
        )

    for number, text in enumerate(source.code_lines, start=1):
        if not GEOMETRY_RE.search(text) or not ARITHMETIC_RE.search(text):
            continue
        window = source.raw_lines[max(0, number - 3) : number]
        if any("//" in candidate for candidate in window):
            continue
        findings.append(
            Finding(
                source.display,
                number,
                "LAY-10",
                "geometry arithmetic without a derivation comment — fix the cause or write the derivation down",
            )
        )

    return findings


# --------------------------------------------------------------------------
# Colors rules
# --------------------------------------------------------------------------


def check_color_literals(source: SourceFile) -> List[Finding]:
    findings: List[Finding] = []

    for number, text in enumerate(source.code_lines, start=1):
        for pattern, form in COLOR_LITERAL_PATTERNS:
            if pattern.search(text):
                findings.append(
                    Finding(
                        source.display,
                        number,
                        "COL-05",
                        "inline color literal {} — a view references a semantic token".format(form),
                        context="preview" if number in source.preview_lines else "",
                    )
                )

    for number, strings in enumerate(source.string_lines, start=1):
        if not strings:
            continue
        code = source.code_lines[number - 1]
        if not re.search(r"\b(Color|UIColor|NSColor)\s*\(", code):
            continue
        for literal in strings:
            if HEX_STRING_RE.fullmatch(literal.strip()):
                findings.append(
                    Finding(
                        source.display,
                        number,
                        "COL-05",
                        "hex string {} passed to a color initializer".format(literal),
                        context="preview" if number in source.preview_lines else "",
                    )
                )

    return findings


def check_palette_references(
    source: SourceFile, palette_symbols: Sequence[str], semantic_paths: Sequence[str]
) -> List[Finding]:
    if not palette_symbols:
        return []
    if any(matches_glob(source.display, pattern) for pattern in semantic_paths):
        return []

    findings: List[Finding] = []
    for number, text in enumerate(source.code_lines, start=1):
        for symbol in palette_symbols:
            if re.search(r"(?<![\w.]){}\b|\.{}\b".format(re.escape(symbol), re.escape(symbol)), text):
                findings.append(
                    Finding(
                        source.display,
                        number,
                        "COL-01",
                        "palette entry '{}' referenced outside the semantic layer".format(symbol),
                    )
                )
                break
    return findings


def colorset_entries(catalog_roots: Sequence[Path]) -> List[Tuple[str, Path, Tuple]]:
    entries: List[Tuple[str, Path, Tuple]] = []
    for root in catalog_roots:
        if not root.exists():
            continue
        for contents in sorted(root.rglob("*.colorset/Contents.json")):
            name = contents.parent.name[: -len(".colorset")]
            try:
                payload = json.loads(contents.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            for color in payload.get("colors", []):
                components = color.get("color", {}).get("components")
                if not isinstance(components, dict):
                    continue
                appearance = tuple(
                    sorted(
                        (item.get("appearance", ""), item.get("value", ""))
                        for item in color.get("appearances", [])
                        if isinstance(item, dict)
                    )
                )
                key = (
                    appearance,
                    normalize_component(components.get("red")),
                    normalize_component(components.get("green")),
                    normalize_component(components.get("blue")),
                    normalize_component(components.get("alpha")),
                    normalize_component(components.get("white")),
                )
                entries.append((name, contents, key))
    return entries


def normalize_component(value: object) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip()
    try:
        if text.startswith("0x") or text.startswith("0X"):
            return int(text, 16) / 255.0
        number = float(text)
    except ValueError:
        return None
    return round(number / 255.0 if number > 1.0 else number, 4)


def check_palette_catalog(catalog_roots: Sequence[Path], project_root: Path) -> List[Finding]:
    findings: List[Finding] = []
    entries = colorset_entries(catalog_roots)

    by_value: Dict[Tuple, List[Tuple[str, Path]]] = {}
    for name, contents, key in entries:
        by_value.setdefault(key, []).append((name, contents))

    for key, group in sorted(by_value.items(), key=lambda item: sorted(name for name, _ in item[1])):
        if len(group) < 2:
            continue
        names = sorted(name for name, _ in group)
        findings.append(
            Finding(
                display_path(group[0][1], project_root),
                1,
                "COL-02",
                "palette entries with the same value: {} — reuse one entry".format(", ".join(names)),
            )
        )

    # Entries identical except for alpha are the same colour stored twice; the
    # transparency belongs in code as .opacity(...) over the base entry.
    without_alpha: Dict[Tuple, List[Tuple[str, Path, Optional[float]]]] = {}
    for name, contents, key in entries:
        without_alpha.setdefault(key[:4] + key[5:], []).append((name, contents, key[4]))

    for _key, group in sorted(without_alpha.items(), key=lambda item: sorted(n for n, _, _ in item[1])):
        names = sorted({name for name, _, _ in group})
        alphas = {alpha for _, _, alpha in group}
        if len(names) < 2 or len(alphas) < 2:
            continue
        findings.append(
            Finding(
                display_path(group[0][1], project_root),
                1,
                "COL-04",
                "palette entries differing only in alpha: {} — apply .opacity() over one entry".format(
                    ", ".join(names)
                ),
            )
        )

    for name, contents, _key in entries:
        if ALPHA_NAME_RE.search(name):
            findings.append(
                Finding(
                    display_path(contents, project_root),
                    1,
                    "COL-04",
                    "palette entry '{}' encodes alpha in its name — apply .opacity() over the base entry".format(name),
                )
            )

    return findings


# --------------------------------------------------------------------------
# Plumbing
# --------------------------------------------------------------------------


def matches_glob(path: str, pattern: str) -> bool:
    from fnmatch import fnmatch

    return fnmatch(path, pattern) or fnmatch(path, "*/" + pattern.lstrip("/"))


def display_path(path: Path, project_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(project_root.resolve()))
    except ValueError:
        return str(path)


def changed_files(project_root: Path, ref: str) -> List[Path]:
    command = ["git", "-C", str(project_root), "diff", "--name-only", "--diff-filter=ACMR", ref]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError("git diff failed: {}".format(result.stderr.strip()))
    return [project_root / name for name in result.stdout.split("\n") if name.strip()]


def parse_canvas(value: Optional[str]) -> Optional[Tuple[float, float]]:
    if not value:
        return None
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*", value)
    if not match:
        raise ValueError("--reference-canvas expects WIDTHxHEIGHT, e.g. 393x852")
    return (float(match.group(1)), float(match.group(2)))


def apply_waivers(findings: Sequence[Finding], sources: Dict[str, SourceFile]) -> List[Finding]:
    resolved: List[Finding] = []
    for finding in findings:
        source = sources.get(finding.path)
        waived = False
        if source is not None:
            window = source.raw_lines[max(0, finding.line - 2) : finding.line]
            for candidate in window:
                match = WAIVER_RE.search(candidate)
                if match and match.group(1) == finding.rule:
                    waived = True
                    break
        resolved.append(
            Finding(
                finding.path,
                finding.line,
                finding.rule,
                finding.message,
                finding.context,
                waived,
            )
        )
    return resolved


def coverage_note(rules: Sequence[str]) -> List[str]:
    lines = ["Coverage — a clean run means only these rules were checked:"]
    for rule in sorted(CHECKED):
        if rule[:3] in rules:
            lines.append("  checked   {} — {}".format(rule, CHECKED[rule]))
    for rule in sorted(UNCHECKED):
        if rule[:3] in rules:
            lines.append("  reviewer  {} — {}".format(rule, UNCHECKED[rule]))
    return lines


def run_check(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    rules = [item.strip().upper() for item in args.rules.split(",") if item.strip()]

    try:
        canvas = parse_canvas(args.reference_canvas)
    except ValueError as error:
        print("error: {}".format(error), file=sys.stderr)
        return 2

    paths: List[Path] = [Path(item) for item in args.files]
    if args.changed_since:
        try:
            paths.extend(changed_files(project_root, args.changed_since))
        except RuntimeError as error:
            print("error: {}".format(error), file=sys.stderr)
            return 2

    swift_paths = []
    for path in paths:
        resolved = path if path.is_absolute() else (project_root / path)
        if resolved.suffix not in SWIFT_SUFFIXES or not resolved.is_file():
            continue
        if resolved.stat().st_size > MAX_FILE_BYTES:
            print("skipped (too large): {}".format(display_path(resolved, project_root)), file=sys.stderr)
            continue
        swift_paths.append(resolved)

    sources: Dict[str, SourceFile] = {}
    for path in sorted(set(swift_paths)):
        display = display_path(path, project_root)
        sources[display] = SourceFile(path, display)

    findings: List[Finding] = []
    for source in sources.values():
        if "LAY" in rules:
            findings.extend(check_layout(source, canvas))
        if "COL" in rules:
            findings.extend(check_color_literals(source))
            findings.extend(
                check_palette_references(source, args.palette_symbol, args.semantic_layer)
            )

    if "COL" in rules and args.asset_catalog:
        findings.extend(
            check_palette_catalog(
                [Path(item) if Path(item).is_absolute() else project_root / item for item in args.asset_catalog],
                project_root,
            )
        )

    findings = apply_waivers(findings, sources)
    findings.sort(key=lambda item: (item.path, item.line, item.rule))

    active = [finding for finding in findings if not finding.waived]
    waived = [finding for finding in findings if finding.waived]

    if args.format == "json":
        payload = {
            "clean": not active,
            "files_scanned": len(sources),
            "findings": [finding.as_dict() for finding in findings],
            "checked_rules": sorted(rule for rule in CHECKED if rule[:3] in rules),
            "reviewer_rules": sorted(rule for rule in UNCHECKED if rule[:3] in rules),
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1 if active else 0

    for finding in active[: args.max_findings]:
        print(finding.render(), file=sys.stderr)
    if len(active) > args.max_findings:
        print("... {} more".format(len(active) - args.max_findings), file=sys.stderr)

    for line in coverage_note(rules):
        print(line)

    print(
        "ui-guard: {} findings, {} waived, {} files scanned".format(len(active), len(waived), len(sources))
    )
    print("UI_GUARD_DIRTY" if active else "UI_GUARD_CLEAN")
    return 1 if active else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Detect Layout (LAY) and Colors (COL) contract violations in Swift sources."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="Check files against the LAY and COL detections")
    check.add_argument("files", nargs="*", help="Swift files to check")
    check.add_argument(
        "--changed-since",
        help="Add files changed since this git ref (e.g. the feature's base SHA)",
    )
    check.add_argument("--project-root", default=".", help="Project root for relative paths (default: .)")
    check.add_argument("--rules", default="LAY,COL", help="Rule families to run (default: LAY,COL)")
    check.add_argument(
        "--reference-canvas",
        help="Design reference canvas WIDTHxHEIGHT; sharpens LAY-01 (e.g. 393x852)",
    )
    check.add_argument(
        "--asset-catalog",
        action="append",
        default=[],
        help="Asset catalog root to scan for palette entries (repeatable); enables COL-02 and COL-04",
    )
    check.add_argument(
        "--palette-symbol",
        action="append",
        default=[],
        help="Palette symbol name a view must not reference (repeatable); enables COL-01",
    )
    check.add_argument(
        "--semantic-layer",
        action="append",
        default=[],
        help="Path glob owning the semantic layer, exempt from COL-01 (repeatable)",
    )
    check.add_argument("--format", choices=("text", "json"), default="text")
    check.add_argument("--max-findings", type=int, default=50)
    check.set_defaults(handler=run_check)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
