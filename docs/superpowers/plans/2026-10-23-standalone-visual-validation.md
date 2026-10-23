# Standalone Visual Validation Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement the tasks in order. Track completion below; retain the user's existing template-numbering changes.

**Goal:** Extract stages 5 and 6 into independently invocable `figma-design-compare` and `swiftui-adaptivity-check`, also called by `figma-full-cycle`, without duplicate rules or scripts.

**Architecture:** Each new skill owns its workflow and completion criteria. Stage references become pipeline adapters. Shared contracts and three read-only helpers live once in `skills/_figma-full-cycle-shared/`; the installer includes that non-skill resource directory whenever a consuming skill is selected. Standalone validation writes its own report, needs no pipeline state, and adaptivity supports a no-Figma path.

**Tech Stack:** Markdown skills, YAML UI metadata, Bash installer, Python 3.9+ standard library helpers and unittest, existing Node device-recorder tests.

**Spec:** User request in this chat: extract stages 5/6 with the exact names above, independent use, orchestrator invocation, and one source for rules/scripts. Preserve stage gates and existing standalone skill behavior.

## Global Constraints

- Keep Figma read-only and respect project conventions; physical-device checks stay optional unless required.
- Preserve real geometry and visual evidence; a mechanical PASS alone never closes visual verification.
- No pipeline manifest, UI Plan, Git branch or commit is required in standalone mode.
- No Figma URL, credential or mock is required for standalone adaptivity without design comparison.
- Python remains 3.9+ and standard-library only; install selections fail before mutation when required resources are missing.
- Preserve existing user changes. Work in the current checkout; do not publish or install into the user's real skill directories.

## Review Focus

- Copied standalone installations resolve every required reference and helper without the source checkout or full-cycle skill.
- Missing Figma/mock and missing `sips` lead to reviewed native screenshots, never fabricated references or a false clean marker.
- Namespace-prefixed skill invocation and separate validation-tool roles avoid self-recursion.
- Shared resource installation, replacement and uninstall preserve other consuming skills.
- Pipeline-only token, manifest and stale-result requirements remain explicit at the stage adapters.

## Task 1: Resource ownership and installation

**Files:** `install.sh`, `tools/lint_skills.py`, `tools/tests/test_install.py`, `tools/tests/test_package.py`, `skills/_figma-full-cycle-shared/`, existing consumers, `check.sh`.

**Interfaces:** `<shared-root>` is the sibling `_figma-full-cycle-shared` directory. It owns shared Figma/UI contracts and `screenshot_diff.py`, `ui_guard.py`, `localization_context.py`; pipeline-only helpers remain under the orchestrator.

- [x] Add meaningful installer/package tests for six entry points, dependency closure, copied standalone helper execution, optional device isolation and shared resource preservation.
- [x] Run those tests before implementation and confirm failures identify absent skills/resources.
- [x] Move canonical shared resources, update callers and relative links, and implement installer resource dependencies with preflight validation.
- [x] Run installer/package tests and shared helper suites.

## Task 2: Independent workflows and pipeline adapters

**Files:** new skills and `agents/openai.yaml`; shared validation context/report contract; stage-5/6 adapters; capability discovery, orchestrator, adapter maps and manifest template.

**Interfaces:** Standalone reports contain scope, project constraints, per-screen/configuration evidence and results. Pipeline calls reuse existing state and return compact results; only the orchestrator writes its manifest and commits.

- [x] Inspect baseline behavioral evaluation.
- [x] Extract comparison and adaptivity workflows with one authority for each rule, preserving all original gates.
- [x] Implement native adaptivity without a Figma/mock dependency and avoid manufacturing mechanical comparisons.
- [x] Bind the new bundled skills separately from their optional visual-tool capabilities; bump pipeline schema for added required role bindings.
- [x] Run structural/link checks and independent forward scenarios, then fix demonstrated gaps.

## Task 3: Distribution documentation and final verification

**Files:** plugin manifests, both READMEs, CONTRIBUTING, CHANGELOG, existing tests/check runner as needed.

- [x] Document six entry points, shared resource location, standalone installation and usage.
- [x] Run `./check.sh` and `git diff --check`; inspect final changes.
- [x] Request an independent read-only review focused on copied installs, workflow boundaries and preserved gates; address material findings and rerun affected checks.

## Progress

- Planning: complete. Implementation proceeds in this chat under the user's explicit request; no further approach decision is needed.

- Tasks 1–3: complete. Baseline evaluation confirmed pipeline bookkeeping and mock-only dependencies; forward evaluation confirmed standalone and pipeline modes and found the now pipeline-only digest-helper route.
- Independent final review: addressed all three P2 findings. Installer-owned symlinks now convert to copies under `--copy` (mixed-mode and same-skill tests observed RED then GREEN); image import is scoped to implementation/authorized fixes; LAY-11 explicitly requires both smallest and largest native captures.
- Verification: `./check.sh` passed (177 Python tests, 9 Node tests, six-skill/link lint and shell syntax). Final `git diff --check` passed. Shared helper bytes match their pre-move versions.
- YAML/UI metadata was validated with Ruby's standard YAML parser; the external skill-creator quick validator lacked PyYAML in this environment. Repository structural checks passed.
- Live Figma access and application/device execution were outside this source/package extraction; no such results are claimed. No user installation, commit, push or publication was performed.
