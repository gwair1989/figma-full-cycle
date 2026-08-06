#!/usr/bin/env python3
"""Structural checks for the skills in this repository.

Verifies that every skill has a well-formed SKILL.md frontmatter, that its declared
name matches its directory, and that relative links inside skill documents resolve.
Standard library only, so it runs anywhere the skills themselves run.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "skills"

NAME_RE = re.compile(r"^name:\s*(.+?)\s*$", re.MULTILINE)
DESCRIPTION_RE = re.compile(r"^description:\s*(.+?)\s*$", re.MULTILINE)
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
MAX_DESCRIPTION = 1024


def frontmatter(text: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    return None if end == -1 else text[4:end]


def check_skill(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    rel = skill_dir.relative_to(REPO_ROOT)
    skill_md = skill_dir / "SKILL.md"

    if not skill_md.is_file():
        return [f"{rel}: missing SKILL.md"]

    text = skill_md.read_text(encoding="utf-8")
    head = frontmatter(text)
    if head is None:
        return [f"{rel}/SKILL.md: missing YAML frontmatter delimited by ---"]

    name_match = NAME_RE.search(head)
    if not name_match:
        errors.append(f"{rel}/SKILL.md: frontmatter has no 'name'")
    else:
        name = name_match.group(1).strip("'\"")
        if name != skill_dir.name:
            errors.append(
                f"{rel}/SKILL.md: name '{name}' does not match directory '{skill_dir.name}'"
            )
        if not SLUG_RE.match(name):
            errors.append(f"{rel}/SKILL.md: name '{name}' is not a lowercase-hyphen slug")

    description_match = DESCRIPTION_RE.search(head)
    if not description_match:
        errors.append(f"{rel}/SKILL.md: frontmatter has no 'description'")
    elif len(description_match.group(1)) > MAX_DESCRIPTION:
        errors.append(
            f"{rel}/SKILL.md: description is {len(description_match.group(1))} chars "
            f"(limit {MAX_DESCRIPTION})"
        )

    for doc in sorted(skill_dir.rglob("*.md")):
        doc_rel = doc.relative_to(REPO_ROOT)
        for target in LINK_RE.findall(doc.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            # Templates carry placeholders like {{FIGMA_URL}} or <FEATURE>; not real paths.
            if any(marker in target for marker in ("{{", "<", "$")):
                continue
            resolved = (doc.parent / target.split("#", 1)[0]).resolve()
            if not resolved.exists():
                errors.append(f"{doc_rel}: broken relative link '{target}'")

    return errors


def main() -> int:
    if not SKILLS_DIR.is_dir():
        print(f"error: {SKILLS_DIR} not found", file=sys.stderr)
        return 1

    skill_dirs = sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir())
    if not skill_dirs:
        print(f"error: no skills in {SKILLS_DIR}", file=sys.stderr)
        return 1

    errors: list[str] = []
    for skill_dir in skill_dirs:
        errors.extend(check_skill(skill_dir))

    if errors:
        for error in errors:
            print(f"ERROR {error}", file=sys.stderr)
        return 1

    print(f"OK {len(skill_dirs)} skills: " + ", ".join(p.name for p in skill_dirs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
