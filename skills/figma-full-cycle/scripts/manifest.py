#!/usr/bin/env python3
"""Read parts of a pipeline manifest, and check whether contract sources moved.

The manifest is the feature's source of truth and it grows: by stage 6 a filled
one runs tens of kilobytes. A stage that re-reads all of it pays for every other
stage's evidence, on every stage, for the rest of the run.

`sections` and `get` read a named part instead of the file. `verify-sources`
answers the one question a resume actually has — did the documents the contract
was resolved from change — by comparing recorded digests against the files on
disk, so an unchanged project costs one command instead of re-reading its
documentation.

Read-only by construction: nothing here writes to the manifest. The main thread
stays the only writer.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


MAX_MANIFEST_BYTES = 8_000_000
DIGEST_CHARS = 12
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
CONTRACT_HEADING_RE = re.compile(r"project ui convention contract", re.IGNORECASE)
# `docs/architecture.md#layout @ 3f2a1b9c4d5e` — the anchor is for humans, the
# digest covers the whole file.
SOURCE_RE = re.compile(r"(?<![\w/.])([\w./~-]+\.[\w]+)(#[\w.-]+)?\s*@\s*([0-9a-fA-F]{8,64})")


@dataclass(frozen=True)
class Section:
    level: int
    title: str
    start: int
    end: int

    @property
    def line_count(self) -> int:
        return self.end - self.start + 1


@dataclass(frozen=True)
class SourceRef:
    area: str
    path: str
    anchor: str
    digest: str


def read_manifest(path: Path) -> List[str]:
    if not path.is_file():
        raise RuntimeError("manifest not found: {}".format(path))
    if path.stat().st_size > MAX_MANIFEST_BYTES:
        raise RuntimeError("manifest is larger than {} bytes: {}".format(MAX_MANIFEST_BYTES, path))
    return path.read_text(encoding="utf-8").splitlines()


def parse_sections(lines: Sequence[str]) -> List[Section]:
    """Every heading, with the line range it owns.

    A section ends before the next heading at the same or a higher level, so
    asking for a parent brings its subsections along.
    """
    headings: List[Tuple[int, int, str]] = []
    fenced = False
    for number, line in enumerate(lines, start=1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        match = HEADING_RE.match(line)
        if match:
            headings.append((number, len(match.group(1)), match.group(2)))

    sections: List[Section] = []
    for index, (start, level, title) in enumerate(headings):
        end = len(lines)
        for later_start, later_level, _later_title in headings[index + 1 :]:
            if later_level <= level:
                end = later_start - 1
                break
        sections.append(Section(level=level, title=title, start=start, end=end))
    return sections


def select_sections(sections: Sequence[Section], query: str) -> List[Section]:
    needle = query.strip().lower()
    exact = [section for section in sections if section.title.strip().lower() == needle]
    if exact:
        return exact
    return [section for section in sections if needle in section.title.lower()]


def contract_sources(lines: Sequence[str], sections: Sequence[Section]) -> List[SourceRef]:
    """Parse `path @ digest` tokens out of the UI convention contract table."""
    contract = next((section for section in sections if CONTRACT_HEADING_RE.search(section.title)), None)
    if contract is None:
        return []

    refs: List[SourceRef] = []
    for line in lines[contract.start : contract.end]:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 2:
            continue
        area = cells[0]
        if not area or area.lower() in {"area", "------"} or set(area) <= set("-: "):
            continue
        for match in SOURCE_RE.finditer(" ".join(cells[1:])):
            refs.append(
                SourceRef(
                    area=area,
                    path=match.group(1),
                    anchor=(match.group(2) or "").lstrip("#"),
                    digest=match.group(3).lower(),
                )
            )
    return refs


def contract_areas(lines: Sequence[str], sections: Sequence[Section]) -> List[str]:
    contract = next((section for section in sections if CONTRACT_HEADING_RE.search(section.title)), None)
    if contract is None:
        return []

    areas: List[str] = []
    for line in lines[contract.start : contract.end]:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells:
            continue
        area = cells[0]
        if not area or area.lower() == "area" or set(area) <= set("-: "):
            continue
        if area not in areas:
            areas.append(area)
    return areas


def digest_file(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_sections(args: argparse.Namespace) -> int:
    lines = read_manifest(Path(args.file))
    sections = parse_sections(lines)
    if not sections:
        print("no headings found", file=sys.stderr)
        return 1

    for section in sections:
        print(
            "{indent}{title}  ({lines} lines, {level})".format(
                indent="  " * (section.level - 1),
                title=section.title,
                lines=section.line_count,
                level="#" * section.level,
            )
        )
    print("\n{} sections, {} lines total".format(len(sections), len(lines)))
    return 0


def run_get(args: argparse.Namespace) -> int:
    lines = read_manifest(Path(args.file))
    sections = parse_sections(lines)

    chosen: List[Section] = []
    missing: List[str] = []
    for query in args.section:
        matches = select_sections(sections, query)
        if not matches:
            missing.append(query)
            continue
        for match in matches:
            if match not in chosen:
                chosen.append(match)

    for query in missing:
        print("no section matching: {}".format(query), file=sys.stderr)

    chosen.sort(key=lambda section: section.start)
    for index, section in enumerate(chosen):
        if index:
            print()
        for line in lines[section.start - 1 : section.end]:
            print(line)

    if missing:
        print(
            "\navailable: {}".format(", ".join(section.title for section in sections)),
            file=sys.stderr,
        )
        return 1
    return 0


def run_digest(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    exit_code = 0
    for name in args.paths:
        path = Path(name)
        resolved = path if path.is_absolute() else project_root / path
        full = digest_file(resolved)
        if full is None:
            print("missing: {}".format(name), file=sys.stderr)
            exit_code = 1
            continue
        print("{} @ {}".format(name, full[:DIGEST_CHARS]))
    return exit_code


def run_verify_sources(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    lines = read_manifest(Path(args.file))
    sections = parse_sections(lines)

    refs = contract_sources(lines, sections)
    areas = contract_areas(lines, sections)
    if not areas:
        print("no UI convention contract table in the manifest", file=sys.stderr)
        return 2

    by_area: Dict[str, List[SourceRef]] = {}
    for ref in refs:
        by_area.setdefault(ref.area, []).append(ref)

    stale = 0
    for area in areas:
        recorded = by_area.get(area, [])
        if not recorded:
            print("{:<14} unrecorded  no digest — re-read this area, it cannot be skipped".format(area))
            stale += 1
            continue

        problems: List[str] = []
        for ref in recorded:
            path = Path(ref.path)
            resolved = path if path.is_absolute() else project_root / path
            full = digest_file(resolved)
            if full is None:
                problems.append("{} (missing)".format(ref.path))
            elif not full.startswith(ref.digest):
                problems.append("{} (was {}, now {})".format(ref.path, ref.digest, full[:DIGEST_CHARS]))

        if problems:
            print("{:<14} CHANGED     {}".format(area, "; ".join(problems)))
            stale += 1
        else:
            print("{:<14} unchanged   {} source(s)".format(area, len(recorded)))

    print(
        "\n{} of {} areas need a re-read".format(stale, len(areas))
        if stale
        else "\nall {} areas unchanged — reuse the resolved contract".format(len(areas))
    )
    return 1 if stale else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read parts of a pipeline manifest and check contract source digests."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    sections = subparsers.add_parser("sections", help="List the manifest's sections and their size")
    sections.add_argument("--file", required=True, help="Path to <FEATURE>_PIPELINE.md")
    sections.set_defaults(handler=run_sections)

    get = subparsers.add_parser("get", help="Print named sections instead of the whole manifest")
    get.add_argument("--file", required=True, help="Path to <FEATURE>_PIPELINE.md")
    get.add_argument(
        "--section",
        action="append",
        required=True,
        help="Section title or a substring of it (repeatable)",
    )
    get.set_defaults(handler=run_get)

    digest = subparsers.add_parser("digest", help="Print `path @ digest` lines to record in the manifest")
    digest.add_argument("paths", nargs="+", help="Contract source files")
    digest.add_argument("--project-root", default=".")
    digest.set_defaults(handler=run_digest)

    verify = subparsers.add_parser(
        "verify-sources", help="Compare recorded contract source digests against the files on disk"
    )
    verify.add_argument("--file", required=True, help="Path to <FEATURE>_PIPELINE.md")
    verify.add_argument("--project-root", default=".")
    verify.set_defaults(handler=run_verify_sources)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.handler(args)
    except RuntimeError as error:
        print("error: {}".format(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
