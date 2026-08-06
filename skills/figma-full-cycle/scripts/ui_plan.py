#!/usr/bin/env python3
"""Validate a compact, project-aware UI implementation plan.

The validator intentionally does not generate SwiftUI. It verifies the
machine-readable handoff between Figma/spec analysis and implementation so
that an agent receives small, actionable diagnostics before a build loop.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


MAX_PLAN_BYTES = 2_000_000
NODE_ID_RE = re.compile(r"^\d+[:-]\d+$")
IDENTIFIER_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
PLACEHOLDER_RE = re.compile(r"<[A-Z][A-Z0-9_]*>")
SKILL_ROOT = Path(__file__).resolve().parents[1]
BUNDLED_TEMPLATE = (SKILL_ROOT / "templates" / "UI_PLAN.template.json").resolve()

VIEW_STATUSES = {"existing", "new", "tbd"}
COMPONENT_KINDS = {"system", "project", "new"}
TOKEN_KINDS = {"system", "project"}
RESOLUTION_STATUSES = {"resolved", "tbd"}
STATE_SOURCES = {"figma", "spec", "user", "project", "tbd"}
INTERACTION_SOURCES = {"spec", "user", "figma-prototype", "tbd"}
INTERACTION_STATUSES = {"resolved", "tbd", "waived"}
UNKNOWN_STATUSES = {"open", "tbd", "resolved", "waived"}
SOURCE_KINDS = {"figma", "project-doc", "code", "spec", "user"}


@dataclass(frozen=True)
class Diagnostic:
    path: str
    actual: Any
    expected: str
    hint: str

    def render(self) -> str:
        try:
            actual = json.dumps(self.actual, ensure_ascii=False)
        except (RecursionError, TypeError, ValueError):
            actual = f'"<{type(self.actual).__name__}>"'
        if len(actual) > 500:
            actual = actual[:497] + "..."
        return f"ERROR {self.path}: {actual}; expected {self.expected}. Hint: {self.hint}"


def contains_placeholder(value: Any) -> bool:
    return isinstance(value, str) and bool(PLACEHOLDER_RE.search(value))


def format_allowed(values: Iterable[str]) -> str:
    return "allowed: " + ", ".join(sorted(values))


def strip_markdown_cell(value: str) -> str:
    return value.strip().strip(chr(96)).strip()


def markdown_section(text: str, *heading_prefixes: str) -> str | None:
    """Body of the first section whose heading starts with one of the prefixes.

    Accepting several prefixes keeps manifests created from the earlier Russian
    templates validating after the templates were translated.
    """
    for heading_prefix in heading_prefixes:
        pattern = re.compile(
            rf"^##\s+{re.escape(heading_prefix)}[^\n]*\n(?P<body>.*?)(?=^##\s+|\Z)",
            re.MULTILINE | re.DOTALL,
        )
        match = pattern.search(text)
        if match:
            return match.group("body")
    return None


def table_column_values(
    section: str | None,
    column: int,
    expected_header: str,
) -> tuple[set[str], bool]:
    if section is None:
        return set(), False
    lines = section.splitlines()
    for index, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            continue
        cells = [strip_markdown_cell(cell) for cell in line.strip().strip("|").split("|")]
        if len(cells) <= column or cells[column].lower() != expected_header.lower():
            continue
        if index + 1 >= len(lines) or not lines[index + 1].lstrip().startswith("|"):
            continue
        separator_cells = [
            strip_markdown_cell(cell)
            for cell in lines[index + 1].strip().strip("|").split("|")
        ]
        if len(separator_cells) != len(cells) or not all(
            cell and set(cell) <= {"-", ":", " "} for cell in separator_cells
        ):
            continue
        values: set[str] = set()
        for row in lines[index + 2 :]:
            if not row.lstrip().startswith("|"):
                break
            row_cells = [
                strip_markdown_cell(cell) for cell in row.strip().strip("|").split("|")
            ]
            if len(row_cells) <= column:
                continue
            value = row_cells[column]
            if value:
                values.add(value)
        return values, True
    return set(), False


def manifest_references(
    text: str,
) -> tuple[set[str], set[str], bool, bool, bool, bool]:
    copy_section = markdown_section(text, "Feature copy inventory")
    asset_section = markdown_section(
        text, "Sub-checklist: assets", "Под-чеклист: ассеты"
    )
    copy_ids, has_copy_table = table_column_values(copy_section, 0, "Copy ID")
    asset_node_ids, has_asset_table = table_column_values(asset_section, 1, "node-id")
    return (
        copy_ids,
        asset_node_ids,
        copy_section is not None,
        asset_section is not None,
        has_copy_table,
        has_asset_table,
    )


class Validator:
    def __init__(
        self,
        *,
        phase: str,
        allow_placeholders: bool,
        manifest_text: str | None,
        manifest_path: Path | None,
        project_root: Path | None,
    ) -> None:
        self.phase = phase
        self.allow_placeholders = allow_placeholders
        self.project_root = project_root
        self.manifest_path = manifest_path
        self.diagnostics: list[Diagnostic] = []
        self.copy_ids: set[str] | None = None
        self.asset_node_ids: set[str] | None = None
        if manifest_text is not None:
            (
                self.copy_ids,
                self.asset_node_ids,
                has_copy_section,
                has_asset_section,
                has_copy_table,
                has_asset_table,
            ) = manifest_references(manifest_text)
            if not has_copy_section:
                self.error(
                    "$.project_contract.manifest",
                    None,
                    "a ## Feature copy inventory section",
                    "Create the section from templates/PIPELINE.template.md, even when its table is empty.",
                )
            if not has_asset_section:
                self.error(
                    "$.project_contract.manifest",
                    None,
                    "a ## Sub-checklist: assets section",
                    "Create the section from templates/PIPELINE.template.md, even when its table is empty.",
                )
            if has_copy_section and not has_copy_table:
                self.error(
                    "$.project_contract.manifest",
                    None,
                    "a contiguous Markdown table headed by Copy ID",
                    "Restore the Feature copy inventory table from templates/PIPELINE.template.md.",
                )
            if has_asset_section and not has_asset_table:
                self.error(
                    "$.project_contract.manifest",
                    None,
                    "a contiguous Markdown table with a node-id column",
                    "Restore the asset checklist table from templates/PIPELINE.template.md.",
                )
        if not allow_placeholders:
            if manifest_text is None:
                self.error(
                    "$",
                    None,
                    "--manifest for a feature validation",
                    "Pass the tracked pipeline manifest; omit it only for template self-checks.",
                )
            if self.project_root is None:
                self.error(
                    "$",
                    None,
                    "--project-root for a feature validation",
                    "Pass the repository root so project paths and symbols are actually checked.",
                )

    def error(self, path: str, actual: Any, expected: str, hint: str) -> None:
        self.diagnostics.append(Diagnostic(path, actual, expected, hint))

    def mapping(self, parent: dict[str, Any], key: str, path: str) -> dict[str, Any]:
        value = parent.get(key)
        if isinstance(value, dict):
            return value
        self.error(path, value, "an object", f"Add an object at {path}.")
        return {}

    def sequence(
        self,
        parent: dict[str, Any],
        key: str,
        path: str,
        *,
        nonempty: bool = False,
    ) -> list[Any]:
        value = parent.get(key)
        if not isinstance(value, list):
            self.error(path, value, "an array", f"Add an array at {path}.")
            return []
        if nonempty and not value:
            self.error(path, value, "a non-empty array", f"Add at least one item to {path}.")
        return value

    def string(
        self,
        parent: dict[str, Any],
        key: str,
        path: str,
        *,
        identifier: bool = False,
    ) -> str:
        value = parent.get(key)
        if not isinstance(value, str) or not value.strip():
            self.error(path, value, "a non-empty string", f"Set {path} explicitly.")
            return ""
        value = value.strip()
        has_placeholder = contains_placeholder(value)
        if has_placeholder and not self.allow_placeholders:
            self.error(
                path,
                value,
                "a concrete value without <PLACEHOLDER>",
                "Resolve the placeholder before running a feature gate.",
            )
        elif identifier and not (self.allow_placeholders and has_placeholder) and not IDENTIFIER_RE.fullmatch(value):
            self.error(
                path,
                value,
                "a lowercase identifier matching [a-z0-9][a-z0-9._-]*",
                "Use a stable machine identifier; keep the human label in name.",
            )
        return value

    def enum(
        self,
        parent: dict[str, Any],
        key: str,
        path: str,
        allowed: set[str],
    ) -> str:
        value = self.string(parent, key, path)
        if value and value not in allowed:
            self.error(path, value, format_allowed(allowed), f"Replace {value!r} with a supported value.")
        return value

    def boolean(self, parent: dict[str, Any], key: str, path: str) -> bool:
        value = parent.get(key)
        if not isinstance(value, bool):
            self.error(path, value, "true or false", f"Set {path} explicitly.")
            return False
        return value

    def validate_waiver(self, parent: dict[str, Any], path: str) -> None:
        waiver = parent.get("waiver")
        if not isinstance(waiver, dict):
            self.error(
                path,
                waiver,
                "an object with reason and evidence",
                "Document who/what authorized the waiver and link its evidence.",
            )
            return
        self.string(waiver, "reason", f"{path}.reason")
        self.string(waiver, "evidence", f"{path}.evidence")

    def node_id(self, parent: dict[str, Any], key: str, path: str) -> str:
        value = self.string(parent, key, path)
        if (
            value
            and not (self.allow_placeholders and contains_placeholder(value))
            and not NODE_ID_RE.fullmatch(value)
        ):
            self.error(
                path,
                value,
                "a Figma node ID such as 123:456",
                "Copy node-id from the Figma URL or metadata.",
            )
        return value

    def safe_relative_path(self, value: str, path: str) -> Path | None:
        if not value or (self.allow_placeholders and contains_placeholder(value)):
            return None
        relative = Path(value)
        if relative.is_absolute() or ".." in relative.parts:
            self.error(
                path,
                value,
                "a relative path inside --project-root",
                "Remove absolute or '..' path segments.",
            )
            return None
        return relative

    def resolve_project_path(
        self,
        relative: Path | None,
        relative_text: str,
        path: str,
    ) -> Path | None:
        if self.project_root is None or relative is None:
            return None
        try:
            candidate = (self.project_root / relative).resolve()
        except (OSError, RuntimeError, ValueError):
            self.error(
                path,
                relative_text,
                "a valid project-relative path",
                "Remove invalid path characters or symlink loops and retry.",
            )
            return None
        try:
            candidate.relative_to(self.project_root)
        except ValueError:
            self.error(
                path,
                relative_text,
                "a path resolving inside --project-root",
                "Use a repository-relative path that does not escape through a symlink.",
            )
            return None
        return candidate

    def validate_source_ref(self, value: Any, path: str) -> None:
        if not isinstance(value, dict):
            self.error(
                path,
                value,
                "an object with path and symbol",
                "Point to the exact project source file and symbol.",
            )
            return
        relative_text = self.string(value, "path", f"{path}.path")
        symbol = self.string(value, "symbol", f"{path}.symbol")
        relative = self.safe_relative_path(relative_text, f"{path}.path")
        if self.project_root is None or relative is None:
            return

        candidate = self.resolve_project_path(relative, relative_text, f"{path}.path")
        if candidate is None:
            return

        if not candidate.is_file():
            self.error(
                f"{path}.path",
                relative_text,
                "an existing project source file",
                "Audit the project component/token and record its exact file.",
            )
            return

        if not symbol or (self.allow_placeholders and contains_placeholder(symbol)):
            return
        try:
            content = candidate.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            self.error(f"{path}.path", relative_text, "a readable source file", str(exc))
            return
        symbol_pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(symbol)}(?![A-Za-z0-9_])")
        if not symbol_pattern.search(content):
            self.error(
                f"{path}.symbol",
                symbol,
                f"a symbol present in {relative_text}",
                "Correct the symbol or source_ref path; do not invent a project component.",
            )

    def validate_plan(self, value: Any) -> list[Diagnostic]:
        if not isinstance(value, dict):
            self.error("$", value, "a JSON object", "Start from templates/UI_PLAN.template.json.")
            return self.diagnostics

        version = value.get("schema_version")
        if type(version) is not int or version != 1:
            self.error(
                "$.schema_version",
                version,
                "integer 1",
                "Migrate the plan to the current bundled template before resume.",
            )
        self.string(value, "feature", "$.feature", identifier=True)
        figma_pin = self.mapping(value, "figma_pin", "$.figma_pin")
        self.string(figma_pin, "file_key", "$.figma_pin.file_key")
        self.node_id(figma_pin, "parent_node_id", "$.figma_pin.parent_node_id")
        self.string(figma_pin, "version", "$.figma_pin.version")

        contract = self.mapping(value, "project_contract", "$.project_contract")
        manifest_path = self.string(contract, "manifest", "$.project_contract.manifest")
        manifest_relative = self.safe_relative_path(manifest_path, "$.project_contract.manifest")
        if (
            self.project_root is not None
            and self.manifest_path is not None
            and manifest_relative is not None
        ):
            expected_manifest = self.resolve_project_path(
                manifest_relative,
                manifest_path,
                "$.project_contract.manifest",
            )
            if expected_manifest is not None and expected_manifest != self.manifest_path:
                self.error(
                    "$.project_contract.manifest",
                    str(self.manifest_path),
                    f"--manifest resolving to {expected_manifest}",
                    "Pass the manifest declared by the UI Plan or correct the contract path.",
                )
        self.string(contract, "checked_base", "$.project_contract.checked_base")

        screens = self.sequence(value, "screens", "$.screens", nonempty=True)
        screen_ids: set[str] = set()
        screen_states: dict[str, set[str]] = {}
        deferred_targets: list[tuple[str, str, str]] = []
        plan_copy_ids: set[str] = set()
        plan_asset_node_ids: set[str] = set()

        for screen_index, raw_screen in enumerate(screens):
            screen_path = f"$.screens[{screen_index}]"
            if not isinstance(raw_screen, dict):
                self.error(screen_path, raw_screen, "an object", "Use one object per screen.")
                continue
            screen = raw_screen
            screen_id = self.string(screen, "id", f"{screen_path}.id", identifier=True)
            if screen_id in screen_ids and screen_id:
                self.error(
                    f"{screen_path}.id",
                    screen_id,
                    "a unique screen id",
                    "Remove the duplicate; represent variants in figma_nodes/states.",
                )
            screen_ids.add(screen_id)
            self.string(screen, "name", f"{screen_path}.name")

            figma_nodes = self.sequence(screen, "figma_nodes", f"{screen_path}.figma_nodes", nonempty=True)
            node_ids: set[str] = set()
            node_state_refs: list[tuple[str, str]] = []
            for node_index, raw_node in enumerate(figma_nodes):
                node_path = f"{screen_path}.figma_nodes[{node_index}]"
                if not isinstance(raw_node, dict):
                    self.error(node_path, raw_node, "an object", "Record node_id and state.")
                    continue
                node_id = self.node_id(raw_node, "node_id", f"{node_path}.node_id")
                if node_id in node_ids and node_id:
                    self.error(
                        f"{node_path}.node_id",
                        node_id,
                        "a unique node within the screen",
                        "Remove duplicate node mappings.",
                    )
                node_ids.add(node_id)
                node_state = self.string(raw_node, "state", f"{node_path}.state", identifier=True)
                node_state_refs.append((f"{node_path}.state", node_state))

            view = self.mapping(screen, "view", f"{screen_path}.view")
            view_symbol = self.string(view, "symbol", f"{screen_path}.view.symbol")
            view_path = self.string(view, "path", f"{screen_path}.view.path")
            view_relative = self.safe_relative_path(view_path, f"{screen_path}.view.path")
            view_candidate = self.resolve_project_path(
                view_relative,
                view_path,
                f"{screen_path}.view.path",
            )
            view_status = self.enum(view, "status", f"{screen_path}.view.status", VIEW_STATUSES)
            if (
                view_status == "existing"
                or (self.phase == "production" and view_status == "new")
            ) and view_symbol and view_path and (
                self.project_root is None or view_candidate is not None
            ):
                self.validate_source_ref(
                    {"path": view_path, "symbol": view_symbol},
                    f"{screen_path}.view",
                )
            if view_status == "tbd":
                self.error(
                    f"{screen_path}.view.status",
                    view_status,
                    "existing or new before stage 3",
                    "Resolve the target view mapping or record a blocking question.",
                )

            layout = self.sequence(screen, "layout", f"{screen_path}.layout", nonempty=True)
            layout_ids: set[str] = set()
            parents: list[tuple[str, Any, str]] = []
            root_count = 0
            for item_index, raw_item in enumerate(layout):
                item_path = f"{screen_path}.layout[{item_index}]"
                if not isinstance(raw_item, dict):
                    self.error(item_path, raw_item, "an object", "Record one layout/component node.")
                    continue
                item_id = self.string(raw_item, "id", f"{item_path}.id", identifier=True)
                if item_id in layout_ids and item_id:
                    self.error(
                        f"{item_path}.id",
                        item_id,
                        "a unique layout id",
                        "Rename or merge duplicate layout nodes.",
                    )
                layout_ids.add(item_id)
                parent = raw_item.get("parent")
                if parent is None:
                    root_count += 1
                elif not isinstance(parent, str) or not parent.strip():
                    self.error(
                        f"{item_path}.parent",
                        parent,
                        "null or a layout id",
                        "Point to the parent layout node.",
                    )
                else:
                    parents.append((item_id, parent.strip(), f"{item_path}.parent"))
                self.string(raw_item, "relation", f"{item_path}.relation")

                component = self.mapping(raw_item, "component", f"{item_path}.component")
                self.string(component, "symbol", f"{item_path}.component.symbol")
                component_kind = self.enum(
                    component,
                    "kind",
                    f"{item_path}.component.kind",
                    COMPONENT_KINDS,
                )
                source_ref = component.get("source_ref")
                if component_kind == "project":
                    self.validate_source_ref(source_ref, f"{item_path}.component.source_ref")
                elif source_ref is not None:
                    self.validate_source_ref(source_ref, f"{item_path}.component.source_ref")

                tokens = self.sequence(raw_item, "tokens", f"{item_path}.tokens")
                for token_index, raw_token in enumerate(tokens):
                    token_path = f"{item_path}.tokens[{token_index}]"
                    if not isinstance(raw_token, dict):
                        self.error(
                            token_path,
                            raw_token,
                            "an object",
                            "Record token symbol, kind, and source_ref.",
                        )
                        continue
                    self.string(raw_token, "symbol", f"{token_path}.symbol")
                    token_kind = self.enum(raw_token, "kind", f"{token_path}.kind", TOKEN_KINDS)
                    if token_kind == "project":
                        self.validate_source_ref(raw_token.get("source_ref"), f"{token_path}.source_ref")

            if layout and root_count != 1:
                self.error(
                    f"{screen_path}.layout",
                    root_count,
                    "exactly one item with parent=null",
                    "Make the component hierarchy explicit with a single root.",
                )
            for item_id, parent, parent_path in parents:
                if parent not in layout_ids and not (
                    self.allow_placeholders and contains_placeholder(parent)
                ):
                    self.error(
                        parent_path,
                        parent,
                        "an existing layout id",
                        f"Declare parent {parent!r} before implementation.",
                    )
                if item_id and parent == item_id:
                    self.error(
                        parent_path,
                        parent,
                        "a different layout id",
                        "A layout node cannot parent itself.",
                    )

            parent_by_id = {
                item_id: parent
                for item_id, parent, _ in parents
                if item_id and parent in layout_ids and parent != item_id
            }
            reported_cycles: set[frozenset[str]] = set()
            for start in sorted(parent_by_id):
                chain: list[str] = []
                positions: dict[str, int] = {}
                current = start
                while current in parent_by_id:
                    if current in positions:
                        cycle_nodes = chain[positions[current] :]
                        cycle_key = frozenset(cycle_nodes)
                        if cycle_key not in reported_cycles:
                            reported_cycles.add(cycle_key)
                            cycle = " -> ".join(cycle_nodes + [current])
                            self.error(
                                f"{screen_path}.layout",
                                cycle,
                                "an acyclic component hierarchy",
                                "Break the parent cycle so every node reaches the single root.",
                            )
                        break
                    positions[current] = len(chain)
                    chain.append(current)
                    current = parent_by_id[current]

            copy_items = self.sequence(screen, "copy", f"{screen_path}.copy")
            seen_copy_ids: set[str] = set()
            for copy_index, raw_copy in enumerate(copy_items):
                copy_path = f"{screen_path}.copy[{copy_index}]"
                if not isinstance(raw_copy, dict):
                    self.error(copy_path, raw_copy, "an object", "Record copy_id, usage, and status.")
                    continue
                copy_id = self.string(raw_copy, "copy_id", f"{copy_path}.copy_id", identifier=True)
                if copy_id in seen_copy_ids and copy_id:
                    self.error(
                        f"{copy_path}.copy_id",
                        copy_id,
                        "a unique copy id per screen",
                        "Combine repeated usages.",
                    )
                seen_copy_ids.add(copy_id)
                if copy_id:
                    plan_copy_ids.add(copy_id)
                self.string(raw_copy, "usage", f"{copy_path}.usage")
                copy_status = self.enum(raw_copy, "status", f"{copy_path}.status", RESOLUTION_STATUSES)
                if copy_status == "tbd":
                    self.error(
                        f"{copy_path}.status",
                        copy_status,
                        "resolved before stage 3",
                        "Resolve the project string mapping.",
                    )
                if (
                    self.copy_ids is not None
                    and copy_id
                    and not (self.allow_placeholders and contains_placeholder(copy_id))
                    and copy_id not in self.copy_ids
                ):
                    self.error(
                        f"{copy_path}.copy_id",
                        copy_id,
                        "a Copy ID present in the pipeline manifest",
                        "Add or correct the Feature copy inventory row.",
                    )

            assets = self.sequence(screen, "assets", f"{screen_path}.assets")
            seen_assets: set[str] = set()
            for asset_index, raw_asset in enumerate(assets):
                asset_path = f"{screen_path}.assets[{asset_index}]"
                if not isinstance(raw_asset, dict):
                    self.error(asset_path, raw_asset, "an object", "Record node_id, name, and status.")
                    continue
                node_id = self.node_id(raw_asset, "node_id", f"{asset_path}.node_id")
                if node_id in seen_assets and node_id:
                    self.error(
                        f"{asset_path}.node_id",
                        node_id,
                        "a unique asset node per screen",
                        "Remove duplicate asset references.",
                    )
                seen_assets.add(node_id)
                if node_id:
                    plan_asset_node_ids.add(node_id)
                self.string(raw_asset, "name", f"{asset_path}.name")
                asset_status = self.enum(raw_asset, "status", f"{asset_path}.status", RESOLUTION_STATUSES)
                if asset_status == "tbd":
                    self.error(
                        f"{asset_path}.status",
                        asset_status,
                        "resolved before stage 3",
                        "Resolve the asset mapping.",
                    )
                if (
                    self.asset_node_ids is not None
                    and node_id
                    and not (self.allow_placeholders and contains_placeholder(node_id))
                    and node_id not in self.asset_node_ids
                ):
                    self.error(
                        f"{asset_path}.node_id",
                        node_id,
                        "a node-id present in the manifest asset checklist",
                        "Add or correct the stage 2 asset row.",
                    )

            states = self.sequence(screen, "states", f"{screen_path}.states", nonempty=True)
            state_ids: set[str] = set()
            figma_sourced_states: list[tuple[str, str]] = []
            for state_index, raw_state in enumerate(states):
                state_path = f"{screen_path}.states[{state_index}]"
                if not isinstance(raw_state, dict):
                    self.error(state_path, raw_state, "an object", "Record id, source, and status.")
                    continue
                state_id = self.string(raw_state, "id", f"{state_path}.id", identifier=True)
                if state_id in state_ids and state_id:
                    self.error(
                        f"{state_path}.id",
                        state_id,
                        "a unique state id",
                        "Merge or rename duplicate states.",
                    )
                state_ids.add(state_id)
                state_source = self.enum(
                    raw_state,
                    "source",
                    f"{state_path}.source",
                    STATE_SOURCES,
                )
                if state_source == "figma":
                    figma_sourced_states.append((f"{state_path}.source", state_id))
                state_status = self.enum(
                    raw_state,
                    "status",
                    f"{state_path}.status",
                    RESOLUTION_STATUSES,
                )
                if state_status == "resolved" and state_source == "tbd":
                    self.error(
                        f"{state_path}.source",
                        state_source,
                        "figma, spec, user, or project provenance for a resolved state",
                        "Record the evidence source or keep the state status tbd.",
                    )
                if self.phase == "production" and state_status == "tbd":
                    self.error(
                        f"{state_path}.status",
                        state_status,
                        "resolved for production",
                        "Resolve the visual state contract before production readiness.",
                    )

            mapped_figma_states = {state for _, state in node_state_refs if state}
            for state_path, state in node_state_refs:
                if state and state not in state_ids and not (
                    self.allow_placeholders and contains_placeholder(state)
                ):
                    self.error(
                        state_path,
                        state,
                        "a state id declared by this screen",
                        "Add the state contract or correct the Figma node mapping.",
                    )
            for source_path, state_id in figma_sourced_states:
                if state_id and state_id not in mapped_figma_states and not (
                    self.allow_placeholders and contains_placeholder(state_id)
                ):
                    self.error(
                        source_path,
                        state_id,
                        "a state backed by at least one figma_nodes mapping",
                        "Map a Figma node to this state or use the actual state provenance.",
                    )
            screen_states[screen_id] = state_ids

            interactions = self.sequence(screen, "interactions", f"{screen_path}.interactions")
            interaction_ids: set[str] = set()
            for interaction_index, raw_interaction in enumerate(interactions):
                interaction_path = f"{screen_path}.interactions[{interaction_index}]"
                if not isinstance(raw_interaction, dict):
                    self.error(
                        interaction_path,
                        raw_interaction,
                        "an object",
                        "Record the transition contract.",
                    )
                    continue
                interaction_id = self.string(
                    raw_interaction,
                    "id",
                    f"{interaction_path}.id",
                    identifier=True,
                )
                if interaction_id in interaction_ids and interaction_id:
                    self.error(
                        f"{interaction_path}.id",
                        interaction_id,
                        "a unique interaction id",
                        "Merge or rename the interaction.",
                    )
                interaction_ids.add(interaction_id)
                from_state = self.string(
                    raw_interaction,
                    "from",
                    f"{interaction_path}.from",
                    identifier=True,
                )
                to_target = self.string(raw_interaction, "to", f"{interaction_path}.to")
                source = self.string(
                    raw_interaction,
                    "source",
                    f"{interaction_path}.source",
                )
                if source == "figma":
                    self.error(
                        f"{interaction_path}.source",
                        source,
                        format_allowed(INTERACTION_SOURCES),
                        "Static Figma layers are not behavior evidence; use figma-prototype, spec, user, or tbd.",
                    )
                elif source and source not in INTERACTION_SOURCES:
                    self.error(
                        f"{interaction_path}.source",
                        source,
                        format_allowed(INTERACTION_SOURCES),
                        f"Replace {source!r} with a supported value.",
                    )
                status = self.enum(
                    raw_interaction,
                    "status",
                    f"{interaction_path}.status",
                    INTERACTION_STATUSES,
                )
                merge_blocking = self.boolean(
                    raw_interaction,
                    "merge_blocking",
                    f"{interaction_path}.merge_blocking",
                )
                if status == "resolved" and source == "tbd":
                    self.error(
                        f"{interaction_path}.source",
                        source,
                        "spec, user, or figma-prototype provenance for resolved behavior",
                        "Record the behavior evidence or keep the interaction status tbd.",
                    )
                if from_state and from_state not in state_ids and not (
                    self.allow_placeholders and contains_placeholder(from_state)
                ):
                    self.error(
                        f"{interaction_path}.from",
                        from_state,
                        "a state id declared by this screen",
                        "Declare the source state or correct the interaction.",
                    )
                deferred_targets.append((f"{interaction_path}.to", to_target, screen_id))
                if status == "waived":
                    self.validate_waiver(raw_interaction, f"{interaction_path}.waiver")
                if self.phase == "production" and merge_blocking and status not in {
                    "resolved",
                    "waived",
                }:
                    self.error(
                        f"{interaction_path}.status",
                        status,
                        "resolved or waived for merge-blocking production behavior",
                        "Resolve the interaction from spec/user evidence or record an explicit waiver.",
                    )

            sources = self.sequence(screen, "sources", f"{screen_path}.sources", nonempty=True)
            for source_index, raw_source in enumerate(sources):
                source_path = f"{screen_path}.sources[{source_index}]"
                if not isinstance(raw_source, dict):
                    self.error(source_path, raw_source, "an object", "Record kind and ref.")
                    continue
                source_kind = self.enum(
                    raw_source,
                    "kind",
                    f"{source_path}.kind",
                    SOURCE_KINDS,
                )
                source_ref = self.string(raw_source, "ref", f"{source_path}.ref")
                if (
                    source_kind == "figma"
                    and source_ref
                    and source_ref not in node_ids
                    and not (self.allow_placeholders and contains_placeholder(source_ref))
                ):
                    self.error(
                        f"{source_path}.ref",
                        source_ref,
                        "a node_id declared in this screen's figma_nodes",
                        "Use the exact scoped Figma node ID that supports this mapping.",
                    )

            unknowns = self.sequence(screen, "unknowns", f"{screen_path}.unknowns")
            unknown_ids: set[str] = set()
            for unknown_index, raw_unknown in enumerate(unknowns):
                unknown_path = f"{screen_path}.unknowns[{unknown_index}]"
                if not isinstance(raw_unknown, dict):
                    self.error(
                        unknown_path,
                        raw_unknown,
                        "an object",
                        "Record id, question, status, and merge_blocking.",
                    )
                    continue
                unknown_id = self.string(
                    raw_unknown,
                    "id",
                    f"{unknown_path}.id",
                    identifier=True,
                )
                if unknown_id in unknown_ids and unknown_id:
                    self.error(
                        f"{unknown_path}.id",
                        unknown_id,
                        "a unique unknown id",
                        "Merge duplicate questions.",
                    )
                unknown_ids.add(unknown_id)
                self.string(raw_unknown, "question", f"{unknown_path}.question")
                status = self.enum(
                    raw_unknown,
                    "status",
                    f"{unknown_path}.status",
                    UNKNOWN_STATUSES,
                )
                merge_blocking = self.boolean(
                    raw_unknown,
                    "merge_blocking",
                    f"{unknown_path}.merge_blocking",
                )
                if status == "waived":
                    self.validate_waiver(raw_unknown, f"{unknown_path}.waiver")
                if self.phase == "production" and merge_blocking and status not in {
                    "resolved",
                    "waived",
                }:
                    self.error(
                        f"{unknown_path}.status",
                        status,
                        "resolved or waived for a merge-blocking production unknown",
                        "Answer the question or record an explicit waiver before production readiness.",
                    )

        if self.copy_ids is not None:
            missing_copy_ids = sorted(self.copy_ids - plan_copy_ids)
            if missing_copy_ids:
                self.error(
                    "$.screens[*].copy",
                    {"missing_manifest_copy_ids": missing_copy_ids},
                    "every manifest Copy ID mapped by at least one screen",
                    "Add the omitted copy mappings or remove out-of-scope rows from this feature manifest.",
                )
        if self.asset_node_ids is not None:
            missing_asset_ids = sorted(self.asset_node_ids - plan_asset_node_ids)
            if missing_asset_ids:
                self.error(
                    "$.screens[*].assets",
                    {"missing_manifest_asset_node_ids": missing_asset_ids},
                    "every manifest asset node-id mapped by at least one screen",
                    "Add the omitted asset mappings or remove out-of-scope rows from this feature manifest.",
                )

        all_screen_ids = {item for item in screen_ids if item}
        for target_path, target, source_screen in deferred_targets:
            if not target or (self.allow_placeholders and contains_placeholder(target)):
                continue
            source_states = screen_states.get(source_screen, set())
            external_id = target[len("external:") :] if target.startswith("external:") else ""
            is_external = bool(external_id and IDENTIFIER_RE.fullmatch(external_id))
            if (
                target not in source_states
                and target not in all_screen_ids
                and not is_external
            ):
                self.error(
                    target_path,
                    target,
                    "a state id, screen id, or external:<id>",
                    "Make navigation/transition targets explicit.",
                )

        return self.diagnostics


def read_text(path: Path, *, max_bytes: int | None = None) -> str:
    if max_bytes is not None and path.stat().st_size > max_bytes:
        raise ValueError(f"{path} exceeds {max_bytes} bytes")
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> Any:
    try:
        return json.loads(read_text(path, max_bytes=MAX_PLAN_BYTES))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{path}:{exc.lineno}:{exc.colno}: invalid JSON: {exc.msg}"
        ) from exc
    except RecursionError as exc:
        raise ValueError(f"{path}: invalid JSON: nesting exceeds the supported depth") from exc


def validate_command(args: argparse.Namespace) -> int:
    try:
        plan_path = args.plan.resolve()
        if args.allow_placeholders and plan_path != BUNDLED_TEMPLATE:
            raise ValueError(
                "--allow-placeholders is restricted to the bundled templates/UI_PLAN.template.json"
            )
        try:
            project_root = args.project_root.resolve() if args.project_root else None
        except (OSError, RuntimeError, ValueError) as exc:
            raise ValueError(f"invalid --project-root: {exc}") from exc
        if project_root is not None and not project_root.is_dir():
            raise ValueError(f"--project-root is not a directory: {project_root}")
        try:
            manifest_path = args.manifest.resolve() if args.manifest else None
        except (OSError, RuntimeError, ValueError) as exc:
            raise ValueError(f"invalid --manifest: {exc}") from exc
        plan = load_json(plan_path)
        plan_hash = hashlib.sha256(plan_path.read_bytes()).hexdigest()
        manifest_text = read_text(manifest_path) if manifest_path else None
    except (OSError, RecursionError, RuntimeError, ValueError) as exc:
        print(
            f"ERROR $: {json.dumps(str(exc))}; expected readable valid input. "
            "Hint: Fix the file and retry.",
            file=sys.stderr,
        )
        return 1

    validator = Validator(
        phase=args.phase,
        allow_placeholders=args.allow_placeholders,
        manifest_text=manifest_text,
        manifest_path=manifest_path,
        project_root=project_root,
    )
    diagnostics = validator.validate_plan(plan)
    if diagnostics:
        for diagnostic in diagnostics[: args.max_errors]:
            print(diagnostic.render(), file=sys.stderr)
        if len(diagnostics) > args.max_errors:
            print(
                f"ERROR $: {len(diagnostics) - args.max_errors} additional diagnostics hidden; "
                f"expected at most {args.max_errors} displayed. "
                "Hint: Fix the reported contract errors first.",
                file=sys.stderr,
            )
        return 1

    screen_count = len(plan.get("screens", [])) if isinstance(plan, dict) else 0
    print(
        f"UI_PLAN_VALID screens={screen_count} phase={args.phase} "
        f"schema={plan['schema_version']} sha256={plan_hash}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate the compact UI implementation contract used by figma-full-cycle."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="Validate a UI Plan JSON file")
    validate.add_argument(
        "--plan",
        type=Path,
        required=True,
        help="Path to docs/<FEATURE>_UI_PLAN.json",
    )
    validate.add_argument(
        "--manifest",
        type=Path,
        help="Pipeline manifest for feature copy/asset cross-checks (omit only with --allow-placeholders)",
    )
    validate.add_argument(
        "--project-root",
        type=Path,
        help="Repository root for source_ref checks (omit only with --allow-placeholders)",
    )
    validate.add_argument("--phase", choices=("ui", "production"), default="ui")
    validate.add_argument(
        "--allow-placeholders",
        action="store_true",
        help="Permit <PLACEHOLDER> values when self-checking the bundled template",
    )
    validate.add_argument("--max-errors", type=int, default=50)
    validate.set_defaults(handler=validate_command)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
