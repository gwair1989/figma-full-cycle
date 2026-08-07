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

Numeric values are resolved through named constants, because a value with a
name is still the value — a first version matched literals only and so stayed
silent on `.frame(width: OnboardingLayout.width, height: OnboardingLayout.height)`,
the exact fixed-canvas shape LAY-01 exists to catch, while reporting dozens of
lesser findings and looking healthy. Resolution spans every file in the run and
covers the forms a project actually writes: literals, one-line enums, multi-line
declarations, computed properties, `as` casts, any `Type(width:height:)` and one
constant naming another. A qualified reference never falls back to a bare last
component, or an unrelated `Decoy.height` answers for someone else's size.

It stays best-effort and therefore fails closed: a frame pinning both dimensions
counts as the screen unless *provably* smaller, so a form nobody anticipated
becomes a false positive rather than a silent miss. Run `constants` to see
exactly what the resolver read.

Waive a finding in code with a comment on the line or the line above:

    // ui-guard: allow LAY-04 — animated entrance, restored on completion
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


MAX_FILE_BYTES = 2_000_000
SWIFT_SUFFIXES = (".swift",)
# A pinned dimension this large is screen-level when no reference canvas is known.
SCREEN_LEVEL_PT = 300
# Below this share of the canvas in either dimension, a pinned block is artwork.
ARTWORK_RATIO = 0.9

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
# Opens a fixed-size artwork group: inside it, elements are placed against each
# other rather than against the screen, so LAY-04 does not apply. One comment
# covers the whole block — a waiver per element trains the reflex to waive.
COMPOSITION_RE = re.compile(r"//\s*ui-guard:\s*composition\b\s*([^\n]*)")
# Not anchored: `enum K { static let w: CGFloat = 393 }` on one line is ordinary
# Swift, and anchoring the match at the line start silently skipped it.
CONSTANT_RE = re.compile(
    r"(?:^|[{;]\s*)(?:public\s+|private\s+|internal\s+|fileprivate\s+|open\s+)*"
    r"(?:static\s+)?(?:let|var)\s+(\w+)\s*(?::\s*[^=]+?)?\s*=\s*(.+)$"
)
TYPE_RE = re.compile(
    r"^(?:public\s+|private\s+|internal\s+|fileprivate\s+|open\s+|final\s+)*"
    r"(?:enum|struct|class|extension)\s+(\w+)"
)
# `static var width: CGFloat { 393 }` — a computed property is a constant too.
COMPUTED_RE = re.compile(
    r"(?:^|[{;]\s*)(?:public\s+|private\s+|internal\s+|fileprivate\s+|open\s+)*"
    r"(?:static\s+)?var\s+(\w+)\s*:\s*[\w<>\[\], ?]+\s*\{\s*(?:return\s+)?([^{}]+?)\s*\}"
)
WRAPPER_CALL_RE = re.compile(r"^(?:CGFloat|Double|Float|Int)\s*\(\s*([^()]+?)\s*\)$")
CAST_RE = re.compile(r"^(.+?)\s+as[!?]?\s+[\w<>\[\], ?.]+$")
IDENTIFIER_PATH_RE = re.compile(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*$")
MEMBER_RE = re.compile(r"^(.*)\.(width|height)$")
# `CGSize(width: 393, height: 852)` is how a reference canvas is usually written,
# but a project's own `CanvasSize(width:height:)` is the same thing — the label
# pair identifies the shape, not the type name.
SIZE_LITERAL_RE = re.compile(
    r"^[\w.]*\s*\(\s*(?:width|dx)\s*:\s*(.+?)\s*,\s*(?:height|dy)\s*:\s*(.+?)\s*\)$"
)
# `.scaleEffect(configuration.isPressed ? 0.97 : 1)` is the animation case the
# rule explicitly permits, not an adaptation mechanism.
CONDITIONAL_RE = re.compile(r"\?.*:|==|!=|>=|<=|[<>]")
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


EPILOG = """Exit codes: 0 clean, 1 findings, 2 usage error.
The last stdout line is UI_GUARD_CLEAN or UI_GUARD_DIRTY — those two values, nothing else,
safe to grep.

Source annotations:
  // ui-guard: allow LAY-04 — <reason>
      Waives one finding. Put it on the offending line or the line above. Waivers are
      counted in the summary, never hidden.
  // ui-guard: composition <name> — <reason>
      Opens a block of fixed-size artwork whose elements are placed against each other, so
      the fixed-geometry rules LAY-02, LAY-03 and LAY-04 do not apply inside it. Covers the
      braces it opens and the modifiers chained onto them — including the frame declaring the
      block's size — so one comment replaces a waiver per element. Refused when that frame is
      not provably smaller than the screen: a canvas is not artwork. Every composition is
      listed in the output, including one that exempted nothing.

Constants are resolved across every file in the run, through CGSize members and through one
constant naming another. Resolution fails closed: a frame pinning both dimensions counts as
screen-sized unless it provably is not, so an unreadable value never becomes an escape.
"""


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


@dataclass(frozen=True)
class Composition:
    """A block declared as fixed-size artwork, exempt from LAY-04."""

    name: str
    start: int
    end: int

    def covers(self, line: int) -> bool:
        return self.start <= line <= self.end


@dataclass
class Chain:
    """Consecutive lines forming one modifier chain, joined for matching.

    `spans` maps each source line to where it begins in `text`, so a finding
    lands on the line that actually carries the offending modifier rather than
    on whatever line the chain happens to start with. Anchoring at the start is
    what made waivers unusable: a chain can begin on a closing paren belonging
    to an entirely different call, and adding the waiver comment re-split the
    chain and moved the anchor again.
    """

    start_line: int
    line_numbers: List[int]
    text: str
    spans: List[Tuple[int, int]] = field(default_factory=list)

    def line_at(self, offset: int) -> int:
        line = self.start_line
        for start, number in self.spans:
            if start > offset:
                break
            line = number
        return line


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
        self.constants = collect_constants(self.code_lines)
        self.compositions = composition_regions(self.raw_lines, self.code_lines)
        self.composition_hits: List[Tuple[str, int]] = []
        self.refused_compositions: List[str] = []

    def has_text_views(self) -> bool:
        return any(re.search(r"\bText\s*\(", line) for line in self.code_lines)


def strip_noncode(line: str) -> str:
    """Blank string literals, then drop a trailing line comment."""
    blanked = STRING_RE.sub('""', line)
    marker = blanked.find("//")
    if marker != -1:
        blanked = blanked[:marker]
    return blanked


MAX_DECLARATION_LINES = 12


def continued_declaration(code_lines: Sequence[str], index: int) -> str:
    """The line, plus the lines its unclosed brackets or braces run into."""
    parts = [code_lines[index].strip()]
    open_round = parts[0].count("(") - parts[0].count(")")
    # A computed property body: `var w: CGFloat {` with the value below.
    open_curly = 1 if re.search(r"\bvar\s+\w+\s*:[^{}]*\{\s*$", parts[0]) else 0

    cursor = index + 1
    while (open_round > 0 or open_curly > 0) and cursor < len(code_lines):
        if cursor - index > MAX_DECLARATION_LINES:
            break
        text = code_lines[cursor].strip()
        parts.append(text)
        open_round += text.count("(") - text.count(")")
        open_curly += text.count("{") - text.count("}")
        cursor += 1

    return " ".join(parts)


def trim_declaration(value: str) -> str:
    """Drop what belongs to the enclosing block, not to the value.

    `enum K { static let w: CGFloat = 393 }` hands back `393 }`.
    """
    text = value.strip().rstrip(",;")
    while text.endswith("}") and text.count("}") > text.count("{"):
        text = text[:-1].strip().rstrip(",;")
    return text


def collect_constants(code_lines: Sequence[str]) -> Dict[str, str]:
    """Named numeric constants declared in a file, qualified by their type.

    A guard that only understands literals is blind to the ordinary practice of
    naming a value, and that is exactly how the canonical fixed-canvas case
    escaped detection: `.frame(width: OnboardingLayout.width, ...)` reads as an
    unknown symbol while being the very pattern LAY-01 exists to catch.
    """
    constants: Dict[str, str] = {}
    ambiguous: set = set()
    scopes: List[Tuple[int, str]] = []
    depth = 0

    for index, line in enumerate(code_lines):
        stripped = line.strip()

        while scopes and depth <= scopes[-1][0]:
            scopes.pop()

        # The type has to be in scope before the declaration is read: on
        # `enum K { static let w = 393 }` the constant would otherwise be
        # recorded as a bare `w`, and a qualified `K.w` would never find it.
        type_declaration = TYPE_RE.match(stripped)
        if type_declaration and "{" in stripped:
            scopes.append((depth, type_declaration.group(1)))

        # A declaration whose value runs past the line end is ordinary
        # formatting: `CGSize(\n  width: 393,\n  height: 852\n)`. Read it whole
        # before matching, or the value is the string "CGSize(".
        subject = continued_declaration(code_lines, index)

        declaration = CONSTANT_RE.search(subject) or COMPUTED_RE.search(subject)
        if declaration:
            name = declaration.group(1)
            value = trim_declaration(declaration.group(2))
            qualified = "{}.{}".format(scopes[-1][1], name) if scopes else name
            constants[qualified] = value
            if name in constants and constants[name] != value:
                ambiguous.add(name)
            else:
                constants[name] = value

        depth += stripped.count("{") - stripped.count("}")

    for name in ambiguous:
        constants.pop(name, None)
    return constants


def lookup_constant(path: str, constants: Dict[str, str]) -> Optional[str]:
    """The declared expression behind a name.

    A qualified reference never falls through to a bare last component: with one
    constant table for the whole run, `Multi.canvas.height` would otherwise
    happily answer with an unrelated `Decoy.height` from another file — a wrong
    number inside a finding, and worse, a wrong number deciding whether a frame
    is smaller than the screen.
    """
    text = path.strip()
    parts = text.split(".")
    shortest = 1 if len(parts) == 1 else 2
    for start in range(len(parts) - shortest + 1):
        candidate = ".".join(parts[start:])
        value = constants.get(candidate)
        if value is not None and value.strip() != text:
            return value
    return None


def resolve_number(expression: str, constants: Dict[str, str], depth: int = 0) -> Optional[float]:
    """A literal, or a named constant that resolves to one."""
    text = expression.strip()
    if not text or depth > 6:
        return None

    try:
        return float(text)
    except ValueError:
        pass

    cast = CAST_RE.match(text)
    if cast:
        return resolve_number(cast.group(1), constants, depth + 1)

    wrapper = WRAPPER_CALL_RE.match(text)
    if wrapper:
        return resolve_number(wrapper.group(1), constants, depth + 1)

    # `GeometryData.referenceCanvasSize.width` — resolve the size, then the member.
    member = MEMBER_RE.match(text)
    if member:
        base, which = member.group(1), member.group(2)
        base_value = base if SIZE_LITERAL_RE.match(base) else lookup_constant(base, constants)
        seen = 0
        while base_value is not None and seen < 6:
            size = SIZE_LITERAL_RE.match(base_value.strip())
            if size:
                return resolve_number(size.group(1 if which == "width" else 2), constants, depth + 1)
            if not IDENTIFIER_PATH_RE.match(base_value.strip()):
                break
            base_value = lookup_constant(base_value, constants)
            seen += 1
        # A recognised member access resolves through its base or not at all.
        # Falling through would look up the member name on its own, which is how
        # an unrelated constant ends up answering for someone else's size.
        if "." in base:
            return None

    if not IDENTIFIER_PATH_RE.match(text):
        return None

    value = lookup_constant(text, constants)
    if value is None:
        return None
    return resolve_number(value, constants, depth + 1)


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

        spans: List[Tuple[int, int]] = []
        position = 0
        for part, number in zip(parts, numbers):
            spans.append((position, number))
            position += len(part) + 1  # the joining space

        chains.append(
            Chain(
                start_line=index + 1,
                line_numbers=numbers,
                text=" ".join(parts),
                spans=spans,
            )
        )
        index = cursor if cursor > index + 1 else index + 1
    return chains


def composition_regions(raw_lines: Sequence[str], code_lines: Sequence[str]) -> List[Composition]:
    """Blocks opened by a `// ui-guard: composition …` comment.

    The block runs from the marker to where the braces it opens close again. A
    marker with no braces after it covers the single following statement.
    """
    compositions: List[Composition] = []
    for index, line in enumerate(raw_lines):
        match = COMPOSITION_RE.search(line)
        if not match:
            continue
        # `composition Animals — 280x180 artwork` → name `Animals`, the rest is
        # the reason and belongs to the reader, not to the identifier.
        name = re.split(r"\s+[-—:]\s+|\s{2,}", match.group(1).strip(), 1)[0].strip(" -—:")
        name = name or "unnamed"

        start = index + 1
        depth = 0
        opened = False
        end = start
        for cursor in range(index, len(code_lines)):
            text = code_lines[cursor]
            depth += text.count("{") - text.count("}")
            if text.count("{"):
                opened = True
            end = cursor + 1
            if opened and depth <= 0:
                break
            if not opened and cursor > index and text.strip():
                break

        # The modifiers chained onto the block belong to it — including the
        # `.frame(...)` that declares its size, which is what the screen-sized
        # check has to see.
        cursor = end
        while cursor < len(code_lines) and code_lines[cursor].lstrip().startswith("."):
            end = cursor + 1
            cursor += 1

        compositions.append(Composition(name=name, start=start, end=end))
    return compositions


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


def frame_calls(text: str) -> Iterable[Tuple[int, str]]:
    for match in re.finditer(r"\.frame\s*\(", text):
        yield match.start(), balanced_args(text, match.end() - 1)


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


def describe(value: str, number: Optional[float]) -> str:
    """`K.w` alone is unreadable in a finding; `K.w = 393` is actionable."""
    text = value.strip()
    if number is None:
        return text
    if numeric(text) is not None:
        return "{:g}".format(number)
    return "{} = {:g}".format(text, number)


def fixed_extent(value: Optional[str]) -> bool:
    """A frame dimension that pins a size, as opposed to letting it stretch."""
    if value is None:
        return False
    text = value.strip()
    return bool(text) and ".infinity" not in text and text != "nil"


def provably_smaller_than_screen(
    width: Optional[float], height: Optional[float], canvas: Optional[Tuple[float, float]]
) -> bool:
    """Is this pinned frame demonstrably a piece of content rather than the screen?

    Artwork is meaningfully smaller than the screen in at least one dimension —
    a 381×373 illustration on a 393×852 canvas is 44% of its height. Requiring
    *both* dimensions to be small would reject it, and a bare `>= 300` threshold
    rejects anything near the full width of a phone.

    Unknown sizes are never "provably" anything: an unresolved frame is treated
    as the screen, so a value the resolver cannot read fails closed.
    """
    if width is None or height is None:
        return False
    if canvas:
        canvas_width, canvas_height = canvas
        return (
            width <= canvas_width * ARTWORK_RATIO or height <= canvas_height * ARTWORK_RATIO
        )
    return width < SCREEN_LEVEL_PT and height < SCREEN_LEVEL_PT


def check_layout(
    source: SourceFile,
    canvas: Optional[Tuple[float, float]],
    shared_constants: Optional[Dict[str, str]] = None,
) -> List[Finding]:
    findings: List[Finding] = []
    # Layout constants routinely live in their own file — that is the convention
    # this guard is meant to reward, not a case it may ignore. The file's own
    # declarations win over another file's on a name clash.
    constants = dict(shared_constants or {})
    constants.update(source.constants)

    canvas_frames: List[Tuple[int, str]] = []
    # LAY-02/03/04 are the fixed-geometry rules, and fixed geometry is exactly
    # what artwork is made of. They are decided after the canvas frames are
    # known, so a composition can be refused before it exempts anything.
    geometry: List[Finding] = []

    for chain in source.chains:
        text = chain.text

        for frame_offset, args in frame_calls(text):
            line = chain.line_at(frame_offset)
            width = labelled_value(args, "width")
            height = labelled_value(args, "height")
            width_number = resolve_number(width, constants) if width else None
            height_number = resolve_number(height, constants) if height else None

            # Both dimensions pinned is the canvas shape unless the block is
            # provably smaller than the screen. Unresolved sizes fail closed:
            # a value the resolver cannot read must not become an escape.
            if fixed_extent(width) and fixed_extent(height):
                if not provably_smaller_than_screen(width_number, height_number, canvas):
                    canvas_frames.append(
                        (
                            line,
                            "{} × {}".format(describe(width, width_number), describe(height, height_number)),
                        )
                    )

            for label, value, number in (
                ("width", width, width_number),
                ("height", height, height_number),
            ):
                if value is None:
                    continue

                if number is None and ARITHMETIC_RE.search(value):
                    geometry.append(
                        Finding(
                            source.display,
                            line,
                            "LAY-03",
                            "arithmetic inside .frame({}: {}) — an inset is padding, not a subtraction".format(
                                label, value.strip()
                            ),
                        )
                    )
                elif number is not None and number >= SCREEN_LEVEL_PT:
                    geometry.append(
                        Finding(
                            source.display,
                            line,
                            "LAY-03",
                            "screen-level .frame({}: {}) — stretch with maxWidth/maxHeight instead".format(
                                label, describe(value, number)
                            ),
                        )
                    )

                if number is not None and GREEDY_SHAPE_RE.match(text.strip()):
                    geometry.append(
                        Finding(
                            source.display,
                            line,
                            "LAY-02",
                            "hard .frame({}: {}) on a greedy shape — the frame shrinks it".format(
                                label, describe(value, number)
                            ),
                        )
                    )

        position = re.search(r"\.position\s*\(", text)
        if position:
            geometry.append(
                Finding(
                    source.display,
                    chain.line_at(position.start()),
                    "LAY-04",
                    ".position(...) is not a layout mechanism — position with alignment, space with padding, or declare the group a composition",
                )
            )

        offset = re.search(r"\.offset\s*\(", text)
        if offset and not ANIMATION_RE.search(text):
            args = balanced_args(text, offset.end() - 1)
            values = [labelled_value(args, "x"), labelled_value(args, "y")]
            static = [
                value
                for value in values
                if value is not None and resolve_number(value, constants) is not None
            ]
            if static:
                geometry.append(
                    Finding(
                        source.display,
                        chain.line_at(offset.start()),
                        "LAY-04",
                        "static .offset({}) used as layout — allowed only for animation, or inside a declared composition".format(
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
                    chain.line_at(background),
                    "LAY-08",
                    ".background(...) before the stretch frame — it paints the content size, not the screen",
                )
            )

        scale = re.search(r"\.scaleEffect\s*\(", text)
        if scale and source.has_text_views():
            factor = balanced_args(text, scale.end() - 1)
            # A factor driven by state is the animation the rule allows; a
            # static one is scaling used as an adaptation mechanism.
            if not CONDITIONAL_RE.search(factor) and not ANIMATION_RE.search(factor):
                findings.append(
                    Finding(
                        source.display,
                        chain.line_at(scale.start()),
                        "LAY-09",
                        "static scaleEffect({}) over text — rasterized scaling disables re-layout and Dynamic Type".format(
                            factor.strip()
                        ),
                    )
                )

    # A composition exempts its contents from LAY-04 — unless the block is itself
    # screen-sized, which would make the marker a way to license the very
    # fixed-canvas pattern the contract exists to forbid.
    honoured: List[Composition] = []
    for composition in source.compositions:
        canvas_inside = [line for line, _ in canvas_frames if composition.covers(line)]
        if canvas_inside:
            findings.append(
                Finding(
                    source.display,
                    composition.start,
                    "LAY-04",
                    "composition '{}' pins a screen-sized frame (line {}) — a canvas is not artwork, "
                    "the exemption does not apply".format(composition.name, canvas_inside[0]),
                )
            )
            source.refused_compositions.append(composition.name)
            continue
        honoured.append(composition)

    for finding in geometry:
        covering = next((c for c in honoured if c.covers(finding.line)), None)
        if covering is None:
            findings.append(finding)
        else:
            source.composition_hits.append((covering.name, finding.line))

    scale_lines = [
        number for number, text in enumerate(source.code_lines, start=1) if ".scaleEffect(" in text
    ]
    if scale_lines and canvas_frames:
        frame_line, dimensions = canvas_frames[0]
        findings.append(
            Finding(
                source.display,
                scale_lines[0],
                "LAY-01",
                "scaleEffect over a pinned {} frame (line {}) — an aspect-fit of the artboard, not adaptation".format(
                    dimensions, frame_line
                ),
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


def load_sources(
    args: argparse.Namespace, project_root: Path
) -> Tuple[Dict[str, "SourceFile"], Optional[int]]:
    """Every Swift file this run covers, keyed by its display path."""
    paths: List[Path] = [Path(item) for item in args.files]
    if getattr(args, "changed_since", None):
        try:
            paths.extend(changed_files(project_root, args.changed_since))
        except RuntimeError as error:
            print("error: {}".format(error), file=sys.stderr)
            return {}, 2

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
    return sources, None


def run_check(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    rules = [item.strip().upper() for item in args.rules.split(",") if item.strip()]

    try:
        canvas = parse_canvas(args.reference_canvas)
    except ValueError as error:
        print("error: {}".format(error), file=sys.stderr)
        return 2

    sources, error = load_sources(args, project_root)
    if error is not None:
        return error

    # One constant table for the whole run: a name declared in `*Style.swift`
    # and used in a view is the normal shape, not an exotic one. A bare name
    # holding two different values across files resolves to neither.
    shared_constants: Dict[str, str] = {}
    conflicting: set = set()
    for source in sources.values():
        for name, value in source.constants.items():
            if name in shared_constants and shared_constants[name] != value:
                conflicting.add(name)
            else:
                shared_constants[name] = value
    for name in conflicting:
        shared_constants.pop(name, None)

    findings: List[Finding] = []
    for source in sources.values():
        if "LAY" in rules:
            findings.extend(check_layout(source, canvas, shared_constants))
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

    exempted = [
        (source.display, name, line)
        for source in sources.values()
        for name, line in source.composition_hits
    ]

    if args.format == "json":
        payload = {
            "clean": not active,
            "files_scanned": len(sources),
            "findings": [finding.as_dict() for finding in findings],
            "composition_exemptions": [
                {"path": path, "composition": name, "line": line} for path, name, line in sorted(exempted)
            ],
            "checked_rules": sorted(rule for rule in CHECKED if rule[:3] in rules),
            "reviewer_rules": sorted(rule for rule in UNCHECKED if rule[:3] in rules),
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1 if active else 0

    for finding in active[: args.max_findings]:
        print(finding.render(), file=sys.stderr)
    if len(active) > args.max_findings:
        print(
            "... {} more — raise --max-findings (currently {}) or use --format json".format(
                len(active) - args.max_findings, args.max_findings
            ),
            file=sys.stderr,
        )

    # Exemptions are announced, never silent: a composition marker that quietly
    # swallowed a screen's worth of offsets would be worse than no rule.
    by_composition: Dict[Tuple[str, str], List[int]] = {}
    # Every declared composition is listed, including the ones that exempted
    # nothing: a marker nobody sees rot quietly in the source, and the reader
    # cannot tell "no longer needed" from "silently not matching".
    for source in sources.values():
        for composition in source.compositions:
            if composition.name in source.refused_compositions:
                continue  # already reported as a refusal, with its reason
            by_composition.setdefault((source.display, composition.name), [])
    for path, name, line in exempted:
        by_composition.setdefault((path, name), []).append(line)

    for (path, name), lines in sorted(by_composition.items()):
        if not lines:
            print(
                "{}: composition '{}' exempts 0 — nothing inside it is a fixed-geometry finding; "
                "remove the marker or check that it opens the block you meant".format(path, name)
            )
            continue
        print(
            "{}: composition '{}' exempts {} fixed-geometry finding(s) on line(s) {}".format(
                path, name, len(lines), ", ".join(str(line) for line in sorted(lines))
            )
        )

    for line in coverage_note(rules):
        print(line)

    print(
        "ui-guard: {} findings, {} waived, {} exempt by composition, {} files scanned".format(
            len(active), len(waived), len(exempted), len(sources)
        )
    )
    print("UI_GUARD_DIRTY" if active else "UI_GUARD_CLEAN")
    return 1 if active else 0


def run_constants(args: argparse.Namespace) -> int:
    """Show what the resolver reads. Every gap found so far was a declaration
    form nobody could see it failing on — this makes the next one a command."""
    project_root = Path(args.project_root).resolve()
    sources, error = load_sources(args, project_root)
    if error is not None:
        return error

    table: Dict[str, str] = {}
    for source in sources.values():
        table.update(source.constants)

    rows = []
    for name in sorted(table):
        if "." not in name and any(key.endswith("." + name) for key in table):
            continue  # the bare alias of a qualified entry, not a second constant
        number = resolve_number(name, table)
        rows.append((name, table[name], "—" if number is None else "{:g}".format(number)))

    if args.format == "json":
        print(
            json.dumps(
                [{"name": n, "declared": d, "resolved": r} for n, d, r in rows],
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if not rows:
        print("no numeric constants found in {} file(s)".format(len(sources)))
        return 0

    width = max(len(name) for name, _, _ in rows)
    for name, declared, resolved in rows:
        print("{:<{}}  {:>10}   {}".format(name, width, resolved, declared[:60]))
    print(
        "\n{} constant(s) in {} file(s); '—' means the resolver cannot read it, "
        "and a frame it cannot read counts as screen-sized".format(len(rows), len(sources))
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Detect Layout (LAY) and Colors (COL) contract violations in Swift sources.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser(
        "check",
        help="Check files against the LAY and COL detections",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    check.add_argument("files", nargs="*", help="Swift files to check")
    check.add_argument(
        "--changed-since",
        help="Add files changed since this git ref (e.g. the feature's base SHA)",
    )
    check.add_argument("--project-root", default=".", help="Project root for relative paths (default: .)")
    check.add_argument("--rules", default="LAY,COL", help="Rule families to run (default: LAY,COL)")
    check.add_argument(
        "--reference-canvas",
        help=(
            "Design reference canvas WIDTHxHEIGHT (e.g. 393x852). Without it a pinned frame counts "
            "as screen-level at {}pt. With it, a pinned block counts as artwork when either "
            "dimension falls below {} of the canvas — which is what lets a composition be "
            "honoured.".format(SCREEN_LEVEL_PT, ARTWORK_RATIO)
        ),
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
    check.add_argument(
        "--max-findings",
        type=int,
        default=50,
        help="Findings to print before truncating (default %(default)s); --format json is never truncated",
    )
    check.set_defaults(handler=run_check)

    constants = subparsers.add_parser(
        "constants",
        help="Show what the constant resolver reads — use it when a rule is unexpectedly quiet",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    constants.add_argument("files", nargs="*", help="Swift files to read")
    constants.add_argument("--changed-since", help="Add files changed since this git ref")
    constants.add_argument("--project-root", default=".")
    constants.add_argument("--format", choices=("text", "json"), default="text")
    constants.set_defaults(handler=run_constants)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
