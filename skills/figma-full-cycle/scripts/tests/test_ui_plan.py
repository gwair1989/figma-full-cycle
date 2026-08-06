#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]
CLI = SKILL_ROOT / "scripts" / "ui_plan.py"
TEMPLATE = SKILL_ROOT / "templates" / "UI_PLAN.template.json"


def valid_plan() -> dict:
    return {
        "schema_version": 1,
        "feature": "checkout",
        "figma_pin": {
            "file_key": "AbCdEf123",
            "parent_node_id": "10:20",
            "version": "v1",
        },
        "project_contract": {
            "manifest": "docs/checkout_PIPELINE.md",
            "checked_base": "abc123",
        },
        "screens": [
            {
                "id": "checkout-main",
                "name": "Checkout",
                "figma_nodes": [
                    {"node_id": "11:21", "state": "default"},
                    {"node_id": "11:22", "state": "loading"},
                ],
                "view": {
                    "symbol": "CheckoutView",
                    "path": "Sources/Checkout/CheckoutView.swift",
                    "status": "new",
                },
                "layout": [
                    {
                        "id": "root",
                        "parent": None,
                        "relation": "root",
                        "component": {
                            "symbol": "VStack",
                            "kind": "system",
                            "source_ref": None,
                        },
                        "tokens": [],
                    },
                    {
                        "id": "submit",
                        "parent": "root",
                        "relation": "below:summary",
                        "component": {
                            "symbol": "PrimaryButton",
                            "kind": "project",
                            "source_ref": {
                                "path": "Sources/DesignSystem/PrimaryButton.swift",
                                "symbol": "PrimaryButton",
                            },
                        },
                        "tokens": [
                            {
                                "symbol": "Spacing.m",
                                "kind": "project",
                                "source_ref": {
                                    "path": "Sources/DesignSystem/Spacing.swift",
                                    "symbol": "Spacing",
                                },
                            }
                        ],
                    },
                ],
                "copy": [
                    {"copy_id": "checkout.submit", "usage": "submit button", "status": "resolved"}
                ],
                "assets": [
                    {"node_id": "12:30", "name": "checkoutLogo", "status": "resolved"}
                ],
                "states": [
                    {"id": "default", "source": "figma", "status": "resolved"},
                    {"id": "loading", "source": "spec", "status": "resolved"},
                ],
                "interactions": [
                    {
                        "id": "submit-order",
                        "from": "default",
                        "to": "loading",
                        "source": "spec",
                        "status": "resolved",
                        "merge_blocking": True,
                    }
                ],
                "sources": [
                    {"kind": "figma", "ref": "11:21"},
                    {"kind": "project-doc", "ref": "docs/ui.md#buttons"},
                ],
                "unknowns": [],
            }
        ],
    }


def manifest_text() -> str:
    return """# Checkout — Pipeline manifest

## Feature copy inventory (unique semantics only)

| Copy ID | Source copy | Usages | Kind | Resource | Evidence | Translation | Source status |
|---------|-------------|--------|------|----------|----------|-------------|---------------|
| checkout.submit | Submit | checkout button | simple | App.xcstrings | lookup | none | verified |

### Translation handoff batches

| Batch | Copy IDs | Owner | Artifact / evidence | Merge policy / due | Статус |
|-------|----------|-------|---------------------|--------------------|--------|
| H1 | checkout.submit | localization | artifact.md | merge after verification | verified |

## Под-чеклист: ассеты (этап 2)

| Ассет | node-id | Тип | Статус | Проверка |
|-------|---------|-----|--------|----------|
| checkoutLogo | 12:30 | vector | done | exists |
"""


class UIPlanCLITests(unittest.TestCase):
    def run_cli(
        self,
        plan: dict,
        *,
        phase: str = "ui",
        manifest: str | None = None,
        manifest_relative: str | None = None,
        project_files: dict[str, str] | None = None,
        project_symlinks: dict[str, str] | None = None,
        outside_files: dict[str, str] | None = None,
        extra_args: list[str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_path = root / "plan.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            args = [
                sys.executable,
                str(CLI),
                "validate",
                "--plan",
                str(plan_path),
                "--phase",
                phase,
            ]

            project_root: Path | None = None
            if project_files is not None:
                project_root = root / "project"
                project_root.mkdir(parents=True, exist_ok=True)
                for relative, content in project_files.items():
                    path = project_root / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content, encoding="utf-8")
                for relative, content in (outside_files or {}).items():
                    path = root / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content, encoding="utf-8")
                for relative, target in (project_symlinks or {}).items():
                    path = project_root / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.symlink_to(target, target_is_directory=True)
                args.extend(["--project-root", str(project_root)])

            if manifest is not None:
                if project_root is not None:
                    relative = manifest_relative or plan["project_contract"]["manifest"]
                    manifest_path = project_root / relative
                    if not manifest_path.parent.exists():
                        manifest_path.parent.mkdir(parents=True, exist_ok=True)
                else:
                    manifest_path = root / "PIPELINE.md"
                manifest_path.write_text(manifest, encoding="utf-8")
                args.extend(["--manifest", str(manifest_path)])

            if extra_args:
                args.extend(extra_args)

            return subprocess.run(args, text=True, capture_output=True, check=False)

    def test_valid_ui_plan_passes_with_manifest_and_project_sources(self) -> None:
        result = self.run_cli(
            valid_plan(),
            manifest=manifest_text(),
            project_files={
                "Sources/DesignSystem/PrimaryButton.swift": "struct PrimaryButton {}",
                "Sources/DesignSystem/Spacing.swift": "enum Spacing { static let m = 8 }",
            },
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("UI_PLAN_VALID screens=1 phase=ui", result.stdout)
        self.assertIn("schema=1", result.stdout)
        self.assertRegex(result.stdout, r"sha256=[0-9a-f]{64}\b")

    def test_feature_validation_requires_manifest_and_project_root(self) -> None:
        result = self.run_cli(valid_plan())

        self.assertEqual(result.returncode, 1)
        self.assertIn("--manifest", result.stderr)
        self.assertIn("--project-root", result.stderr)

    def test_feature_validation_rejects_unresolved_placeholders(self) -> None:
        plan = valid_plan()
        plan["figma_pin"]["file_key"] = "<FILE_KEY>"

        result = self.run_cli(
            plan,
            manifest=manifest_text(),
            project_files={
                "Sources/DesignSystem/PrimaryButton.swift": "struct PrimaryButton {}",
                "Sources/DesignSystem/Spacing.swift": "enum Spacing { static let m = 8 }",
            },
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("$.figma_pin.file_key", result.stderr)
        self.assertIn("placeholder", result.stderr.lower())

    def test_allow_placeholders_is_restricted_to_bundled_template(self) -> None:
        result = self.run_cli(valid_plan(), extra_args=["--allow-placeholders"])

        self.assertEqual(result.returncode, 1)
        self.assertIn("restricted", result.stderr)

    def test_complete_plan_passes_production_validation(self) -> None:
        result = self.run_cli(
            valid_plan(),
            phase="production",
            manifest=manifest_text(),
            project_files={
                "Sources/Checkout/CheckoutView.swift": "struct CheckoutView {}",
                "Sources/DesignSystem/PrimaryButton.swift": "struct PrimaryButton {}",
                "Sources/DesignSystem/Spacing.swift": "enum Spacing { static let m = 8 }",
            },
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("phase=production", result.stdout)

    def test_invalid_enum_reports_json_path_and_allowed_values(self) -> None:
        plan = valid_plan()
        plan["screens"][0]["view"]["status"] = "generated"

        result = self.run_cli(plan)

        self.assertEqual(result.returncode, 1)
        self.assertIn("$.screens[0].view.status", result.stderr)
        self.assertIn("allowed: existing, new, tbd", result.stderr)

    def test_duplicate_screen_id_is_rejected(self) -> None:
        plan = valid_plan()
        duplicate = deepcopy(plan["screens"][0])
        duplicate["name"] = "Checkout duplicate"
        plan["screens"].append(duplicate)

        result = self.run_cli(plan)

        self.assertEqual(result.returncode, 1)
        self.assertIn("$.screens[1].id", result.stderr)
        self.assertIn("duplicate", result.stderr)

    def test_project_source_path_cannot_escape_project_root(self) -> None:
        plan = valid_plan()
        plan["screens"][0]["layout"][1]["component"]["source_ref"]["path"] = "../Outside.swift"

        result = self.run_cli(plan, project_files={})

        self.assertEqual(result.returncode, 1)
        self.assertIn("$.screens[0].layout[1].component.source_ref.path", result.stderr)
        self.assertIn("inside --project-root", result.stderr)

    def test_missing_project_symbol_is_rejected(self) -> None:
        result = self.run_cli(
            valid_plan(),
            project_files={
                "Sources/DesignSystem/PrimaryButton.swift": "struct SecondaryButton {}",
                "Sources/DesignSystem/Spacing.swift": "enum Spacing { static let m = 8 }",
            },
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("$.screens[0].layout[1].component.source_ref.symbol", result.stderr)
        self.assertIn("PrimaryButton", result.stderr)

    def test_existing_view_symbol_must_exist_in_project_source(self) -> None:
        plan = valid_plan()
        plan["screens"][0]["view"]["status"] = "existing"

        result = self.run_cli(
            plan,
            project_files={
                "Sources/Checkout/CheckoutView.swift": "struct DifferentView {}",
                "Sources/DesignSystem/PrimaryButton.swift": "struct PrimaryButton {}",
                "Sources/DesignSystem/Spacing.swift": "enum Spacing { static let m = 8 }",
            },
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("$.screens[0].view.symbol", result.stderr)
        self.assertIn("CheckoutView", result.stderr)

    def test_new_view_must_exist_by_production_validation(self) -> None:
        result = self.run_cli(
            valid_plan(),
            phase="production",
            project_files={
                "Sources/DesignSystem/PrimaryButton.swift": "struct PrimaryButton {}",
                "Sources/DesignSystem/Spacing.swift": "enum Spacing { static let m = 8 }",
            },
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("$.screens[0].view.path", result.stderr)

    def test_new_view_path_cannot_escape_through_symlink_in_ui_phase(self) -> None:
        result = self.run_cli(
            valid_plan(),
            manifest=manifest_text(),
            project_files={
                "Sources/DesignSystem/PrimaryButton.swift": "struct PrimaryButton {}",
                "Sources/DesignSystem/Spacing.swift": "enum Spacing { static let m = 8 }",
            },
            outside_files={"outside/placeholder": ""},
            project_symlinks={"Sources/Checkout": "../../outside"},
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("$.screens[0].view.path", result.stderr)
        self.assertIn("inside --project-root", result.stderr)

    def test_layout_parent_cycle_is_rejected(self) -> None:
        plan = valid_plan()
        plan["screens"][0]["layout"].extend(
            [
                {
                    "id": "cycle-a",
                    "parent": "cycle-b",
                    "relation": "inside",
                    "component": {"symbol": "Text", "kind": "system"},
                    "tokens": [],
                },
                {
                    "id": "cycle-b",
                    "parent": "cycle-a",
                    "relation": "inside",
                    "component": {"symbol": "Text", "kind": "system"},
                    "tokens": [],
                },
            ]
        )

        result = self.run_cli(plan)

        self.assertEqual(result.returncode, 1)
        self.assertIn("$.screens[0].layout", result.stderr)
        self.assertIn("cycle", result.stderr.lower())

    def test_manifest_references_must_exist(self) -> None:
        plan = valid_plan()
        plan["screens"][0]["copy"][0]["copy_id"] = "checkout.missing"
        plan["screens"][0]["assets"][0]["node_id"] = "99:99"

        result = self.run_cli(plan, manifest=manifest_text())

        self.assertEqual(result.returncode, 1)
        self.assertIn("$.screens[0].copy[0].copy_id", result.stderr)
        self.assertIn("$.screens[0].assets[0].node_id", result.stderr)

    def test_manifest_argument_matches_declared_project_path(self) -> None:
        result = self.run_cli(
            valid_plan(),
            manifest=manifest_text(),
            manifest_relative="docs/different_PIPELINE.md",
            project_files={
                "Sources/DesignSystem/PrimaryButton.swift": "struct PrimaryButton {}",
                "Sources/DesignSystem/Spacing.swift": "enum Spacing { static let m = 8 }",
            },
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("$.project_contract.manifest", result.stderr)

    def test_manifest_path_cannot_escape_through_symlink(self) -> None:
        result = self.run_cli(
            valid_plan(),
            manifest=manifest_text(),
            project_files={
                "Sources/DesignSystem/PrimaryButton.swift": "struct PrimaryButton {}",
                "Sources/DesignSystem/Spacing.swift": "enum Spacing { static let m = 8 }",
            },
            outside_files={"outside_docs/placeholder": ""},
            project_symlinks={"docs": "../outside_docs"},
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("$.project_contract.manifest", result.stderr)
        self.assertIn("inside --project-root", result.stderr)

    def test_manifest_requires_copy_and_asset_sections(self) -> None:
        result = self.run_cli(
            valid_plan(),
            manifest="# Checkout — Pipeline manifest\n",
            project_files={
                "Sources/DesignSystem/PrimaryButton.swift": "struct PrimaryButton {}",
                "Sources/DesignSystem/Spacing.swift": "enum Spacing { static let m = 8 }",
            },
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("Feature copy inventory", result.stderr)
        self.assertIn("Под-чеклист: ассеты", result.stderr)

    def test_manifest_headings_without_expected_tables_are_rejected(self) -> None:
        malformed_manifest = """# Checkout — Pipeline manifest

## Feature copy inventory (unique semantics only)

Inventory will be added later.

## Под-чеклист: ассеты (этап 2)

Assets will be added later.
"""
        result = self.run_cli(
            valid_plan(),
            manifest=malformed_manifest,
            project_files={
                "Sources/DesignSystem/PrimaryButton.swift": "struct PrimaryButton {}",
                "Sources/DesignSystem/Spacing.swift": "enum Spacing { static let m = 8 }",
            },
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("contiguous Markdown table headed by Copy ID", result.stderr)
        self.assertIn("contiguous Markdown table with a node-id column", result.stderr)

    def test_manifest_items_cannot_be_omitted_from_plan(self) -> None:
        expanded_manifest = manifest_text().replace(
            "| checkout.submit | Submit | checkout button | simple | App.xcstrings | lookup | none | verified |",
            "| checkout.submit | Submit | checkout button | simple | App.xcstrings | lookup | none | verified |\n"
            "| checkout.title | Checkout | title | simple | App.xcstrings | lookup | none | verified |",
        ).replace(
            "| checkoutLogo | 12:30 | vector | done | exists |",
            "| checkoutLogo | 12:30 | vector | done | exists |\n"
            "| cardLogo | 12:31 | vector | done | exists |",
        )

        result = self.run_cli(valid_plan(), manifest=expanded_manifest)

        self.assertEqual(result.returncode, 1)
        self.assertIn("checkout.title", result.stderr)
        self.assertIn("12:31", result.stderr)

    def test_figma_node_state_must_reference_declared_state(self) -> None:
        plan = valid_plan()
        plan["screens"][0]["figma_nodes"][0]["state"] = "ghost"

        result = self.run_cli(plan)

        self.assertEqual(result.returncode, 1)
        self.assertIn("$.screens[0].figma_nodes[0].state", result.stderr)

    def test_figma_source_ref_must_reference_screen_node(self) -> None:
        plan = valid_plan()
        plan["screens"][0]["sources"][0]["ref"] = "99:99"

        result = self.run_cli(plan)

        self.assertEqual(result.returncode, 1)
        self.assertIn("$.screens[0].sources[0].ref", result.stderr)

    def test_external_interaction_target_requires_stable_id(self) -> None:
        for invalid_target in ("external:", "external:with spaces", "external:!!!"):
            with self.subTest(invalid_target=invalid_target):
                plan = valid_plan()
                plan["screens"][0]["interactions"][0]["to"] = invalid_target

                result = self.run_cli(
                    plan,
                    manifest=manifest_text(),
                    project_files={
                        "Sources/DesignSystem/PrimaryButton.swift": "struct PrimaryButton {}",
                        "Sources/DesignSystem/Spacing.swift": "enum Spacing { static let m = 8 }",
                    },
                )

                self.assertEqual(result.returncode, 1)
                self.assertIn("$.screens[0].interactions[0].to", result.stderr)

    def test_schema_version_requires_an_exact_integer(self) -> None:
        for invalid_version in (True, 1.0):
            with self.subTest(invalid_version=invalid_version):
                plan = valid_plan()
                plan["schema_version"] = invalid_version

                result = self.run_cli(plan)

                self.assertEqual(result.returncode, 1)
                self.assertIn("$.schema_version", result.stderr)

    def test_invalid_source_path_is_an_actionable_diagnostic(self) -> None:
        plan = valid_plan()
        plan["screens"][0]["layout"][1]["component"]["source_ref"]["path"] = "bad\u0000.swift"

        result = self.run_cli(plan, project_files={})

        self.assertEqual(result.returncode, 1)
        self.assertIn("component.source_ref.path", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_project_root_symlink_loop_is_an_actionable_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_path = root / "plan.json"
            manifest_path = root / "manifest.md"
            loop = root / "loop"
            plan_path.write_text(json.dumps(valid_plan()), encoding="utf-8")
            manifest_path.write_text(manifest_text(), encoding="utf-8")
            loop.symlink_to("loop", target_is_directory=True)

            result = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "validate",
                    "--plan",
                    str(plan_path),
                    "--manifest",
                    str(manifest_path),
                    "--project-root",
                    str(loop),
                ],
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("project-root", result.stderr)

    def test_deep_json_is_an_actionable_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan_path = Path(tmp) / "deep.json"
            plan_path.write_text("[" * 2000 + "0" + "]" * 2000, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(CLI), "validate", "--plan", str(plan_path)],
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Traceback", result.stderr)
        # Depending on the interpreter's recursion limits the deep document either
        # fails to parse or parses into a non-object; both must stay actionable.
        self.assertTrue(
            "invalid JSON" in result.stderr
            or "expected a JSON object" in result.stderr,
            result.stderr[:400],
        )

    def test_waived_merge_blocker_requires_reason_and_evidence(self) -> None:
        plan = valid_plan()
        plan["screens"][0]["interactions"][0].update(
            {"source": "tbd", "status": "waived", "merge_blocking": True}
        )
        plan["screens"][0]["unknowns"] = [
            {
                "id": "checkout-api",
                "question": "Which endpoint submits the order?",
                "status": "waived",
                "merge_blocking": True,
            }
        ]

        result = self.run_cli(plan, phase="production")

        self.assertEqual(result.returncode, 1)
        self.assertIn("$.screens[0].interactions[0].waiver", result.stderr)
        self.assertIn("$.screens[0].unknowns[0].waiver", result.stderr)

    def test_ui_phase_allows_open_behavior_but_production_rejects_it(self) -> None:
        plan = valid_plan()
        plan["screens"][0]["interactions"][0].update(
            {"source": "tbd", "status": "tbd", "merge_blocking": True}
        )
        plan["screens"][0]["unknowns"] = [
            {
                "id": "checkout-api",
                "question": "Which endpoint submits the order?",
                "status": "open",
                "merge_blocking": True,
            }
        ]

        project_files = {
            "Sources/Checkout/CheckoutView.swift": "struct CheckoutView {}",
            "Sources/DesignSystem/PrimaryButton.swift": "struct PrimaryButton {}",
            "Sources/DesignSystem/Spacing.swift": "enum Spacing { static let m = 8 }",
        }
        ui_result = self.run_cli(
            plan,
            phase="ui",
            manifest=manifest_text(),
            project_files=project_files,
        )
        production_result = self.run_cli(
            plan,
            phase="production",
            manifest=manifest_text(),
            project_files=project_files,
        )

        self.assertEqual(ui_result.returncode, 0, ui_result.stderr)
        self.assertEqual(production_result.returncode, 1)
        self.assertIn("$.screens[0].interactions[0].status", production_result.stderr)
        self.assertIn("$.screens[0].unknowns[0].status", production_result.stderr)

    def test_resolved_state_and_interaction_require_real_provenance(self) -> None:
        plan = valid_plan()
        plan["screens"][0]["states"][1].update({"source": "tbd", "status": "resolved"})
        plan["screens"][0]["interactions"][0].update(
            {"source": "tbd", "status": "resolved"}
        )

        result = self.run_cli(
            plan,
            phase="production",
            manifest=manifest_text(),
            project_files={
                "Sources/Checkout/CheckoutView.swift": "struct CheckoutView {}",
                "Sources/DesignSystem/PrimaryButton.swift": "struct PrimaryButton {}",
                "Sources/DesignSystem/Spacing.swift": "enum Spacing { static let m = 8 }",
            },
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("$.screens[0].states[1].source", result.stderr)
        self.assertIn("$.screens[0].interactions[0].source", result.stderr)

    def test_production_rejects_tbd_visual_state(self) -> None:
        plan = valid_plan()
        plan["screens"][0]["states"][1]["status"] = "tbd"

        result = self.run_cli(
            plan,
            phase="production",
            manifest=manifest_text(),
            project_files={
                "Sources/Checkout/CheckoutView.swift": "struct CheckoutView {}",
                "Sources/DesignSystem/PrimaryButton.swift": "struct PrimaryButton {}",
                "Sources/DesignSystem/Spacing.swift": "enum Spacing { static let m = 8 }",
            },
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("$.screens[0].states[1].status", result.stderr)

    def test_evidenced_waiver_can_pass_production(self) -> None:
        plan = valid_plan()
        plan["screens"][0]["interactions"][0].update(
            {
                "source": "tbd",
                "status": "waived",
                "merge_blocking": True,
                "waiver": {
                    "reason": "Backend rollout is tracked separately",
                    "evidence": "owner=payments issue=PAY-42 expires=2026-09-01",
                },
            }
        )

        result = self.run_cli(
            plan,
            phase="production",
            manifest=manifest_text(),
            project_files={
                "Sources/Checkout/CheckoutView.swift": "struct CheckoutView {}",
                "Sources/DesignSystem/PrimaryButton.swift": "struct PrimaryButton {}",
                "Sources/DesignSystem/Spacing.swift": "enum Spacing { static let m = 8 }",
            },
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_bundled_template_self_check_allows_placeholders(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(CLI),
                "validate",
                "--plan",
                str(TEMPLATE),
                "--phase",
                "ui",
                "--allow-placeholders",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("UI_PLAN_VALID", result.stdout)


if __name__ == "__main__":
    unittest.main()
