# <FEATURE> — Pipeline manifest

> The full cycle's source of truth. Only the main thread of the `figma-full-cycle` skill writes here.
> pipeline_schema_version: 16
> run_id: <RUN_ID> <!-- date+slug; new on a fresh start, preserved across resume -->
> Figma: <FIGMA_URL>
> Figma pin: fileKey=<KEY> node=<NODE> version=<VERSION_OR_HASH> checked_at=<TS>
> Base: <BASE_BRANCH> @ <BASE_SHA>
> Branch: feature/<FEATURE>
> Spec: docs/<FEATURE>_SPEC.md
> UI Plan: docs/<FEATURE>_UI_PLAN.json schema=1 sha256=<SHA256> validated_at=<TS> phase=<ui|production> status=<todo|valid|stale>
> Mode: <full | ui-first (stop before logic, waiting for requirements)>
> Readiness: <production-ready | prototype/UI-only (user's choice) | TBD>
> Shared resources: <shared-root> = installed sibling _figma-full-cycle-shared (not a skill)
> Runtime (gitignored, never in a PR): docs/<FEATURE>_PIPELINE.local.md

## Capability ledger (preflight)

> Start during discovery per `references/capability-discovery.md`; finalize `app-architecture` only after the Project architecture contract is resolved. Names go in **exactly as registered** (keep plugin/namespace/resource prefixes). Roles, not names, are what the stages depend on.
> Swept: at=<TS> agent=<AGENT>

| Role | Binding (exact registered name / path) | Kind / origin | Capability evidence | Status | Stages |
|------|----------------------------------------|---------------|---------------------|--------|--------|
| `feature-spec` | `figma-feature-spec` | `skill / repo-internal` | pinned | `ready` | 1 |
| `asset-import` | `import-figma-assets` | `skill / repo-internal` | pinned | `ready` | 2 |
| `strings-inspection` | `<shared-root>/scripts/localization_context.py` | `script / repo-internal` | pinned | `ready` | preflight, 3, 8 |
| `ui-plan-validation` | `scripts/ui_plan.py` | `script / repo-internal` | pinned | `ready` | 1, 3, 7 |
| `layout-color-guard` | `<project guard / shared ui_guard.py>` | `script / <project / repo-internal>` | | `todo` | 3, 8 |
| `manifest-read` | `scripts/manifest.py` | `script / repo-internal` | pinned | `ready` | resume, 1–8 |
| `screenshot-geometry` | `<shared-root>/scripts/screenshot_diff.py` | `script / repo-internal` | pinned (needs `sips`) | `todo` | 5, 6 |
| `design-source-read` | | `mcp-tool / vendor-official` | | `todo` | 1, 2, 3, 5 |
| `design-to-code-workflow` | | `<skill / mcp-resource> / <vendor-official / third-party>` | | `todo` | 1, 3 |
| `platform-design-translator` | | | | `todo` | 3 |
| `platform-ui-idiom` | | | | `todo` | 3, 4 |
| `app-architecture` | | | | `todo` | 3, 7 |
| `test-authoring` | | | | `todo` | 7 |
| `view-refactor` | | | | `todo` | 4 |
| `visual-comparison` | `figma-design-compare` | `skill / repo-internal` | pinned | `ready` | 5 |
| `adaptivity-check` | `swiftui-adaptivity-check` | `skill / repo-internal` | pinned | `ready` | 6 |
| `code-review` | | | | `todo` | 8 |
| `build-run` | | | | `todo` | 0, 3, 5–8 |

Statuses: `ready / degraded / fallback / blocked / stale`. A stage does not start while one of its roles is `blocked` or `stale`. `degraded` and `fallback` do not block, but the affected gate evidence says so. Alternates that lost the selection go in the evidence cell, never as a second binding.

Bundled skill identities use the exact registered invocation name, including plugin namespaces. Add a `physical-device-control` row bound to `device-usage` only when physical iPhone checks are requested; its absence is not a simulator-only blocker.

### Figma access probe

| Probe | Result | Evidence | Status |
|-------|--------|----------|--------|
| Transport | `<remote / desktop>` | | `<ready / blocked>` |
| Identity / auth | `<account or scope, never a token value>` | `whoami at <TS>` | `<ready / blocked>` |
| Node reachability | `<fileKey/node reads / permission / not-found / wrong-transport>` | `get_metadata(parent) at <TS>` | `<ready / blocked>` |
| Read capability set | `<container map, design context, screenshot, variable defs>` | | `<ready / degraded>` |
| Optional capabilities | `<code-connect / motion / absent>` | | `<ready / degraded>` |
| Asset path | `<exact-bytes download / temporary URL + HTTP client>` | | `<ready / degraded / blocked>` |
| Write mode | `disabled` | | `ready` |
| Stage 5 credential | `<FIGMA_ACCESS_TOKEN present / absent>` | presence only | `<ready / stage-5 blocker>` |
| Call budget / rate limit | | | `<ready / degraded>` |

## Project architecture contract (preflight)

> Resolve before stage 1, including in `ui-first`. Project documentation or an explicit user decision selects the architecture; code and installed skills do not. Missing, ambiguous or contradictory documentation → ask the user. Reuse this decision in the spec and stages 3/7; pass it to refactor and review workers too.

| Field | Resolved value | Source / evidence |
|-------|----------------|-------------------|
| Scope / architecture | `<target module; selected architecture>` | `<project document path#section or recorded user decision>` |
| State / data flow | `<state owners; UI binding and interaction interfaces>` | |
| Navigation | `<ownership and integration boundaries>` | |
| Dependencies / async work | `<dependency access; external-work boundaries; testing approach>` | |
| Resolution | `<resolved-from-docs / resolved-from-user / blocked / stale>` | `<checked_at; question-log reference when applicable>` |

Only `resolved-from-docs` or `resolved-from-user` permits architecture-dependent work. On resume, re-read the recorded documentation and reconcile with the saved user decision; an absent contract must be resolved, including for older manifests. A changed decision marks the architecture binding, spec / UI Plan and affected gates `stale`. `manifest.py verify-sources` checks the separate UI contract below, not this record.

## Project UI convention contract (preflight)

> The read-only audit ran before Figma and before the worktree; it moves here right after the manifest is created.
> Checked: base=<BASE_SHA> checked_at=<TS>. On resume, re-check the sources that changed.
>
> Every source is recorded as `path#section @ <digest>` — the digest is the first 12 hex characters
> of the file's SHA-256, from `python3 <skill-root>/scripts/manifest.py digest --project-root . <paths>`.
> On resume, `manifest.py verify-sources --file <this file> --project-root .` re-hashes them and says
> per area `unchanged` / `CHANGED` / `unrecorded`; only a changed area is re-read. An area with no
> digest is `unrecorded` and must be re-read — a blank cell never means "unchanged".

| Area | Project sources (`path#section @ digest`) | Project rule | Skill baseline | Resolved decision | Status |
|------|------------------------------------------|--------------|----------------|-------------------|--------|
| Layout | | | `<shared-root>/references/layout-adaptivity-contract.md` (LAY-01…LAY-13) | `<reference canvas; scaling API; smallest/largest device; orientations; patterns the project forbids>` | `todo` |
| Strings | | | `<shared-root>/references/project-ui-conventions.md#strings-baseline` | | `todo` |
| Typography | | | `<shared-root>/references/project-ui-conventions.md#typography-baseline` | | `todo` |
| Colors | | | `<shared-root>/references/colors-contract.md` (COL-01…COL-10) | `<palette mechanism + naming scheme; semantic layer location; system slots; appearance variants; project guard invocation; literal allowlist>` | `todo` |
| Images | | | `import-figma-assets` + `<shared-root>/references/project-ui-conventions.md#images-baseline` | | `todo` |
| Accessibility | | | `<shared-root>/references/project-ui-conventions.md#accessibility-baseline` | `no-add` unless documentation or the user explicitly requires otherwise | `todo` |

Statuses: `matched / project-specific / skill-fallback / inferred-from-code / conflict / not-applicable`. Stages 1–8 do not start while a row is `todo` or while an open `conflict` affects the stage. For Layout, documentation outranks precedent in existing screens: a pattern documentation marks legacy is not repeatable, and `inferred-from-code` applies only when there is no layout documentation at all. For Accessibility, no explicit requirement → `skill-fallback` with the decision `no-add`; `inferred-from-code` never activates scope. Two project documents stating different rules for the same area is a `conflict` to ask about, never a preference to exercise.

## Figma MCP acquisition (preflight + stage 1)

> Fill per `<shared-root>/references/figma-mcp-acquisition.md`. The list of tools actually available outranks the static catalog; never copy raw MCP payloads or temporary asset URLs here.

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
| 3 | UI implementation + architecture skeleton | `todo` | pipeline(<FEATURE>): stage 3 | |
| 4 | UI refactor (conditional) | `todo` | pipeline(<FEATURE>): stage 4 | `skipped` when there are no findings |
| 5 | Design comparison | `todo` | pipeline(<FEATURE>): stage 5 | |
| 6 | Adaptivity | `todo` | pipeline(<FEATURE>): stage 6 | |
| 7 | Business logic | `todo` | pipeline(<FEATURE>): stage 7 | `waiting_user` (waiting for requirements) in ui-first |
| 8 | Final | `todo` | pipeline(<FEATURE>): stage 8 | |

Statuses: `todo / in_progress / blocked / waiting_user / ready_to_commit / done / stale / skipped / waived`.

Resume: reconcile with git first — `HEAD`, dirty/untracked, `git log --grep "pipeline(<FEATURE>)"`. `ready_to_commit` + a commit exists → `done`; no commit → commit it. Then take the first stage that is neither `done` nor `skipped` → the first open row of its sub-checklist. Never store a SHA in the manifest — recover it from the subject.

The commit subject in the table is the **actual** one from git; one stage = one commit (squashing breaks resume).

## Physical device checks (only when requested)

> Scope: `<not-requested / user request / project requirement>`. Follow `references/device-validation.md`; one connected phone does not cover the full adaptivity matrix. Keep hardware identifiers and private data in the local runtime/cache, not this table. A required blocked, failed, not-run or stale row keeps its stage open.

| Stage / route | Required | Target alias / app build / channel | Expected / observed result | Status / coverage | Reviewed evidence / report |
|---------------|----------|-----------------------------------|----------------------------|-------------------|----------------------------|
| | `<yes / no>` | | | `<passed / failed / blocked / not-run / stale>; <full / partial / none>` | `<local artifact path; capture source; dimensions>` |

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

## UI policy checks (stages 3 and 8)

> One row per detection from `<shared-root>/references/layout-adaptivity-contract.md` and `<shared-root>/references/colors-contract.md`, run over the feature's changed files. A hit is a stage 3 blocker, not a stage 5 remark. `waived` requires a reason and the user's decision. Where the project ships its own guard, record its exact invocation in the detection column and run that instead.
>
> Run: `<exact command>` — the project's guard, or `python3 <shared-root>/scripts/ui_guard.py check --project-root . --changed-since <BASE_SHA> --reference-canvas <W>x<H> --asset-catalog <path>`
> Result: `<UI_GUARD_CLEAN / UI_GUARD_DIRTY>` at `<TS>`, `<n>` findings, `<n>` waived, `<n>` files scanned
>
> The shipped guard fills LAY-01…LAY-04, LAY-08…LAY-10, LAY-12, LAY-13, COL-01, COL-02, COL-04 and COL-05 — and only with the flags those rules need (`--reference-canvas`, `--asset-catalog`, `--palette-symbol`, `--semantic-layer`). LAY-07, LAY-11 and COL-03 are reviewer rows in every run; leaving them `todo` leaves the gate open.

| Rule | Detection | Result (hits / clean) | Status |
|------|-----------|-----------------------|--------|
| LAY-01 fixed canvas + `scaleEffect` | `.scaleEffect(` plus a frame pinning both dimensions — literal or named constant | | `todo` |
| LAY-02 hard frame on `Color`/shape | `Color`/`Rectangle`/`RoundedRectangle` + numeric `.frame(width:`/`height:` | | `todo` |
| LAY-03 hard/derived screen-level size | arithmetic inside `.frame(width:`/`height:`; numeric `width:` ≥ 300 | | `todo` |
| LAY-04 `position`/static `offset` as layout | any `.position(`; `.offset(` outside animation, minus declared fixed-size compositions | | `todo` |
| LAY-07 inset snap (−2…+4pt tolerance) | inset literals in the 14–20 range | | `todo` |
| LAY-08 container modifier order | `.background(` before `.frame(maxWidth: .infinity`; `.ignoresSafeArea()` on a content container | | `todo` |
| LAY-09 `scaleEffect` over text | a **static** `.scaleEffect(` factor in a file with `Text`; state-driven factors are the permitted animation case | | `todo` |
| LAY-10 undocumented geometry arithmetic | `safeAreaInsets`/`geo.` in the view layer without a derivation comment | | `todo` |
| LAY-11 adaptivity evidence | smallest/largest screenshots, home-indicator variants, and declared edge-inset relations | | `todo` |
| LAY-12 app-owned screen mask | rounded clip/corner modifier on a screen-sized or two-axis stretched chain | | `todo` |
| LAY-13 overflow artwork sizing a stack | image larger than reference canvas without a later local screen bound and clip | | `todo` |
| COL-01 palette referenced from a view | a palette symbol used outside the files that own the semantic layer | | `todo` |
| COL-02 duplicate palette entry | two palette entries with equal components | | `todo` |
| COL-03 mixed naming schemes | palette entry names that do not follow the one resolved scheme | | `todo` |
| COL-04 alpha in a palette entry | opacity-suffixed names; entries differing only in alpha | | `todo` |
| COL-05 inline colour literal | every forbidden form enumerated: `Color(red:`, `Color(white:`, `Color(hue:`, `Color(hex:`, `UIColor(`/`NSColor(`, `#colorLiteral` | | `todo` |

Statuses: `todo / clean / hits / fixed / waived`. A clean run of a project guard counts only when its pattern demonstrably covers every form listed for COL-05; an uncovered form is recorded here as a known gap, not as `clean`.

## Adaptivity matrix (stage 6)

Import the complete required matrix and reviewed evidence from bundled `swiftui-adaptivity-check`.
Its workflow and shared LAY-11 contract own configuration selection, measurements and completion
criteria. Include unavailable required rows and translation readiness; the report is the detailed
source, while this table is the pipeline summary.

> Report: `<path>`; companion result: `<passed / failed / blocked>` at `<TS>`
> Mechanical result: `<actual SCREENSHOT_DIFF_CLEAN / SCREENSHOT_DIFF_DIRTY / not-run with reason>`
> Reviewed evidence / measured edge invariants / required physical coverage: `<report rows>`

| Screen | Device | Appearance | Content size | Locale / direction | Orientation | Geometry check | Status | Evidence |
|--------|--------|------------|--------------|--------------------|-------------|----------------|--------|----------|
| | | | | | | `<pass / fail / by-eye>` | `todo` | |

## Question log

| # | Question | Stage | Blocker | Status | Answer / source |
|---|----------|-------|---------|--------|-----------------|
| 1 | | | no | open | |

Statuses: `open` / `answered` / `resolved-from-docs` (name where it was found: spec / README / AGENTS.md / code) / `deferred-to-spec` (ui-first: waiting for requirements, reconcile with them on resume).

## Decisions

<!-- Decisions already made, so nothing is asked twice. Format: date — decision — source. -->

## Design comparison (stage 5)

| Screen | Report | Sizes compared (reference + non-reference) | Geometry check | Looked at by eye | ❌ → fix | Status |
|--------|--------|--------------------------------------------|----------------|------------------|----------|--------|
| | `<report path of the bound visual-comparison tool>/<FEATURE>/...` | `<393×852 + 375×667>` | `<pass / fail / not-run>` | `<which pair, and why that one>` | | |

Import coverage, findings and actual geometry markers/fallbacks from `figma-design-compare`.
Its completion criteria and the shared Layout/Colors contracts are authoritative; keep the report's
reviewed pair identifiers in `Looked at by eye` rather than treating a helper marker as visual review.

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
