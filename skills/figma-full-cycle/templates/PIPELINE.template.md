# <FEATURE> — Pipeline manifest

> The full cycle's source of truth. Only the main thread of the `figma-full-cycle` skill writes here.
> pipeline_schema_version: 7
> run_id: <RUN_ID> <!-- date+slug; new on a fresh start, preserved across resume -->
> Figma: <FIGMA_URL>
> Figma pin: fileKey=<KEY> node=<NODE> version=<VERSION_OR_HASH> checked_at=<TS>
> Base: <BASE_BRANCH> @ <BASE_SHA>
> Branch: feature/<FEATURE>
> Spec: docs/<FEATURE>_SPEC.md
> UI Plan: docs/<FEATURE>_UI_PLAN.json schema=1 sha256=<SHA256> validated_at=<TS> phase=<ui|production> status=<todo|valid|stale>
> Mode: <full | ui-first (stop before logic, waiting for requirements)>
> Readiness: <production-ready | prototype/UI-only (user's choice) | TBD>
> Runtime (gitignored, never in a PR): docs/<FEATURE>_PIPELINE.local.md

## Project UI convention contract (preflight)

> The read-only audit ran before Figma and before the worktree; it moves here right after the manifest is created.
> Checked: base=<BASE_SHA> checked_at=<TS>. On resume, re-check the sources that changed.

| Area | Project sources (path + section/symbol) | Project rule | Skill baseline | Resolved decision | Status |
|------|------------------------------------------|--------------|----------------|-------------------|--------|
| Strings | | | `references/project-ui-conventions.md#strings-baseline` | | `todo` |
| Typography | | | `references/project-ui-conventions.md#typography-baseline` | | `todo` |
| Colors | | | `references/project-ui-conventions.md#colors-baseline` | | `todo` |
| Images | | | `import-figma-assets` + `references/project-ui-conventions.md#images-baseline` | | `todo` |
| Accessibility | | | `references/project-ui-conventions.md#accessibility-baseline` | `no-add` unless documentation or the user explicitly requires otherwise | `todo` |

Statuses: `matched / project-specific / skill-fallback / inferred-from-code / conflict / not-applicable`. Stages 1–8 do not start while a row is `todo` or while an open `conflict` affects the stage. For Accessibility, no explicit requirement → `skill-fallback` with the decision `no-add`; `inferred-from-code` never activates scope.

## Figma MCP acquisition (preflight + stage 1)

> Fill per `references/figma-mcp-acquisition.md`. The list of tools actually available outranks the static catalog; never copy raw MCP payloads or temporary asset URLs here.

| Transport / input | Read capabilities | Optional capabilities | Target | Write mode | Pin / normalized cache evidence | Status |
|-------------------|-------------------|-----------------------|--------|------------|---------------------------------|--------|
| `<remote URL+node / desktop selection→pinned node>` | `<metadata, screenshot, design-context, variable-defs, download-assets>` | `<code-connect / motion / unavailable>` | `language=swift; framework=<EXACT_MAPPING_LABEL / iOS-SwiftUI>` | `disabled` | `<fileKey/node/version + local artifact or none>` | `<ready / degraded / blocked>` |

`degraded` is acceptable when an optional capability is missing and a fallback has been chosen and confirmed. Any Figma mutation requires a separate user request and never joins the normal stage flow.

### Figma source quality

| Criterion | Evidence | Status | Impact / fallback |
|-----------|----------|--------|-------------------|
| Components / instances | | `<ready / degraded / unknown>` | |
| Variables / styles | | `<ready / degraded / unknown>` | |
| Auto Layout / constraints / resize | | `<ready / degraded / unknown>` | |
| Semantic layer / state names | | `<ready / degraded / unknown>` | |
| Prototype / annotations / dev resources | | `<ready / degraded / unknown>` | |
| Code Connect coverage | | `<ready / degraded / unknown>` | `<project audit when absent>` |

`degraded` does not block the whole stage. Block only a required mapping that cannot be resolved through Code Connect, a project audit, or an explicit `new` in the UI Plan.

### Component / token provenance

> One row per component or token in use. The UI Plan holds the resulting target; this table holds the mapping's origin and verification.

| Figma node / variable | Kind | Mapping source | Project target (path + symbol) | Label / mapping version | Validation evidence | Status |
|-----------------------|------|----------------|--------------------------------|-------------------------|---------------------|--------|
| | `<component / token>` | `<code-connect / project-audit / new / tbd>` | | | | `<verified / unmapped / stale / blocked>` |

A Code Connect mapping is a candidate until the project path/symbol and the SwiftUI label are verified. Its absence is not by itself a blocker; `unmapped/stale` requires a project audit, an explicit `new`, or a `tbd` with the matching gate.

## Strings snapshot (preflight; compact)

> Fill for the affected Strings scope after reading project documentation and running one read-only inventory. Documentation decides the mechanism; the helper only confirms facts. Never copy catalog values or raw output here.

| Field | Resolved value | Source / evidence |
|-------|----------------|-------------------|
| Mechanism | `<xcstrings-auto / xcstrings-manual / xcstrings-generated-symbols / strings / strings+stringsdict / project-specific / not-applicable>` | `<doc path + section>` |
| Owner / resources | `<target/module; catalog/table; bundle; paths>` | `<doc or inferred symbol>` |
| API / key style | `<allowed API; natural/opaque convention>` | `<doc or representative call sites>` |
| Extraction / symbols | `<mode/settings; generation workflow>` | `<doc + build setting>` |
| Locales | `<source; supported; fallback>` | `<doc>` |
| Translation policy | `<owner; may agent write translations?; TBD flow>` | `<doc>` |
| Variants / comments | `<placeholders; plural/device variants; translator comments; owner of variation structure>` | `<doc>` |
| Validation | `<project build/tests/lint>` | `<doc>` |
| Compact inventory | `<catalog paths/types/counts/locales/states; no values>` | `localization_context.py inventory`, checked_at=`<TS>` |
| Strings base | `<STRINGS_BASE_SHA>` | `<git>` |

## Feature copy inventory (unique semantics only)

> One row per unique meaning and translator context, listing usages together. Never duplicate identical copy per screen and never store a full catalog here. Add accessibility copy only under an active Accessibility contract.

| Copy ID | Source copy | Usages (compact screen/state/control refs) | Kind / params / translator context | Resource path / catalog / table / bundle | Resolved key/symbol + allocation/lookup evidence | Translation batch/status | Source status |
|---------|-------------|--------------------------------------------|------------------------------------|------------------------------------------|--------------------------------------------------|--------------------------|---------------|
| | | | `<simple / interpolation / plural / variant>` | | | `<none / H1:pending / H1:verified>` | `todo` |

Source statuses: `todo / reuse / new / TBD / implemented / verified`. Stage 1 closes after one complete batched lookup (no `MATCHES_TRUNCATED`) and a resolution for every key; stage 3 closes after an exact path-qualified `repo-path::key` `diff --strict`, `validate`, a project build, and every affected source string turning `verified`. Reuse without a physical change does not belong in the diff expectations. Translation readiness and merge policy come only from project documentation and are never masked by the source status.

### Translation handoff batches (only when the project requires them)

| Batch | Copy IDs | Owner | Artifact / evidence | Merge policy / due | Status |
|-------|----------|-------|---------------------|--------------------|--------|
| H1 | | | | | `<pending / handed-off / verified / waived>` |

## Stages

| # | Stage | Status | Commit subject | Note |
|---|-------|--------|----------------|------|
| 0 | Worktree + toolchain | `todo` | pipeline(<FEATURE>): stage 0 | |
| 1 | Spec + UI Plan | `todo` | pipeline(<FEATURE>): stage 1 | |
| 2 | Assets | `todo` | pipeline(<FEATURE>): stage 2 | |
| 3 | UI implementation + TCA skeleton | `todo` | pipeline(<FEATURE>): stage 3 | |
| 4 | UI refactor (conditional) | `todo` | pipeline(<FEATURE>): stage 4 | `skipped` when there are no findings |
| 5 | Design comparison | `todo` | pipeline(<FEATURE>): stage 5 | |
| 6 | Adaptivity | `todo` | pipeline(<FEATURE>): stage 6 | |
| 7 | Reducer logic | `todo` | pipeline(<FEATURE>): stage 7 | `waiting_user` (waiting for requirements) in ui-first |
| 8 | Final | `todo` | pipeline(<FEATURE>): stage 8 | |

Statuses: `todo / in_progress / blocked / waiting_user / ready_to_commit / done / stale / skipped / waived`.

Resume: reconcile with git first — `HEAD`, dirty/untracked, `git log --grep "pipeline(<FEATURE>)"`. `ready_to_commit` + a commit exists → `done`; no commit → commit it. Then take the first stage that is neither `done` nor `skipped` → the first open row of its sub-checklist. Never store a SHA in the manifest — recover it from the subject.

The commit subject in the table is the **actual** one from git; one stage = one commit (squashing breaks resume).

## Gate evidence

| Stage | Command / tool | Time | Result (exit/outcome) | Artifact |
|-------|----------------|------|------------------------|----------|
| | | | | |

## UI Plan evidence

> Fill after every successful `ui_plan.py validate`; copy `schema` and `sha256` from the `UI_PLAN_VALID` line. Any change to the Figma pin, the resolved project contract or the UI Plan itself makes this record `stale` until revalidation.

| Artifact | Schema | Figma pin | SHA-256 | Validation command | Phase / result | validated_at |
|----------|--------|-----------|---------|--------------------|----------------|--------------|
| `docs/<FEATURE>_UI_PLAN.json` | `1` | `fileKey=<KEY> node=<NODE> version=<VERSION_OR_HASH>` | `<SHA256>` | `python3 <skill-root>/scripts/ui_plan.py validate --plan docs/<FEATURE>_UI_PLAN.json --manifest docs/<FEATURE>_PIPELINE.md --project-root . --phase <ui|production>` | `<ui|production> / valid` | `<TS>` |

## Sub-checklist: assets (stage 2)

| Asset | node-id | Type | Status | Check (exists / size / hash) |
|-------|---------|------|--------|------------------------------|
| | | raster/vector | `todo` | |

## Sub-checklist: screens (stages 3 / 5)

| Screen | View | Implementation (3) | Comparison (5) | Figma version at comparison |
|--------|------|--------------------|----------------|-----------------------------|
| | | `todo` | `todo` | |

## Adaptivity matrix (stage 6)

One row per combination. The set comes from the deployment target, the spec, and the Strings, Typography and Accessibility contracts: smallest + largest screen; light/dark; permitted content sizes; supported locales and directions and long copy; orientations if supported; keyboard and safe area. Add AX/VoiceOver/Reduce Motion/increased contrast and other accessibility-only rows only when Accessibility scope is explicitly active; the `no-add` baseline does not create them.

| Screen | Device | Appearance | Content size | Locale / direction | Orientation | Status | Evidence |
|--------|--------|------------|--------------|--------------------|-------------|--------|----------|
| | | | | | | `todo` | |

## Question log

| # | Question | Stage | Blocker | Status | Answer / source |
|---|----------|-------|---------|--------|-----------------|
| 1 | | | no | open | |

Statuses: `open` / `answered` / `resolved-from-docs` (name where it was found: spec / README / AGENTS.md / code) / `deferred-to-spec` (ui-first: waiting for requirements, reconcile with them on resume).

## Decisions

<!-- Decisions already made, so nothing is asked twice. Format: date — decision — source. -->

## Design comparison (stage 5)

| Screen | Report | ❌ → fix | Status |
|--------|--------|----------|--------|
| | design-compare-reports/<FEATURE>/... | | |

## TBD / stubs (stage 7)

| What | Reason | merge-blocking | Waiver (owner / issue / due) | Status |
|------|--------|----------------|------------------------------|--------|
| | | | | |

`production-ready` is impossible while a merge-blocking TBD is open without a waiver.

## Gate failures (loop-back)

> Keep full stdout/stderr as a separate local artifact; only a compact diagnostic record goes here. After the third failed repair loop, stop and ask the user to decide.

| Failure ID | Stage / item | Attempt | Compact diagnostic (path:line/symbol; actual → expected) | Raw log artifact | Change / hypothesis | Result / next action |
|------------|--------------|---------|----------------------------------------------------------|------------------|---------------------|----------------------|
| | | `1/3` | | | | |
