# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `scripts/ui_guard.py` — the LAY and COL detections as a real command instead of prose: reports
  `path:line: RULE-ID: message` over the feature's changed files, so a gate costs findings rather
  than a read of the diff. Covers LAY-01…LAY-04, LAY-08…LAY-10, COL-01, COL-02, COL-04 and COL-05
  (every literal form enumerated), takes `--changed-since`, `--reference-canvas`, `--asset-catalog`,
  `--palette-symbol` and `--semantic-layer`, waives a line via `// ui-guard: allow LAY-04 — reason`,
  and prints with every run a coverage note naming the rules it did **not** check — a clean run is
  only as wide as that note. New `layout-color-guard` role: the project's own guard when it has one,
  the shipped script otherwise.
- `scripts/screenshot_diff.py` — the stage 5 and 6 screenshot check, mechanically. Normalizes the
  mock to the render's size with `sips`, then answers the four LAY-11 questions — letterbox,
  pillarbox, clipped content, background reaching the edges — plus a coarse structural diff, in
  ~0.3s per pair, with a `batch` mode for the stage 6 matrix (~10s for 30 rows instead of 30 images
  in context). Comparing sizes that differ is the point: at the reference size a fixed-canvas layout
  matches pixel-for-pixel and hides the breakage. `--ignore-top/--ignore-bottom` cut the status bar
  and home indicator, both inputs are converted to sRGB, and an alpha channel in either input is
  flagged. Needs `sips`, which ships with macOS — the pipeline already requires macOS for
  `xcrun simctl`, so nothing is installed and the stdlib-only promise holds. New
  `screenshot-geometry` role; without `sips` the fallback is comparing every pair by eye and
  recording that the filter did not run.

  It is a filter and never the gate: it prints with every run what it is blind to — typeface, icon
  shape, copy, colour shifts under the threshold — and the manifest now has a `Looked at by eye`
  column that is never empty, because a screen whose rows all passed mechanically has still not been
  compared to its design.
- `scripts/manifest.py` — read-only manifest access. `sections` and `get` read the parts a stage
  needs instead of a file that runs tens of kilobytes by stage 6; `digest` and `verify-sources`
  answer the question a resume actually has — did the documents the UI convention contract was
  resolved from change — by comparing recorded SHA-256 digests against disk, per area
  `unchanged` / `CHANGED` / `unrecorded`. An unchanged project costs one command instead of a
  re-read of its documentation. New `manifest-read` role; its fallback is reading the manifest whole,
  so the script is an optimization and never a dependency.
- `docs/.cache/<FEATURE>/` — a gitignored artifact root for every byte that must exist but must not
  enter context: cached Figma responses keyed by the Figma pin, screenshots, subagent reports, build
  logs. A loop-back or a targeted re-run reads from disk instead of re-spending MCP calls; clearing
  the cache costs calls and time, never state.
- `references/pitfalls.md` — the full failure catalog, grouped by stage and area so a dirty gate can
  read its own group. `SKILL.md` keeps the twelve costliest.
- `references/stages/stage-1.md` … `stage-8.md` — role binding, fallbacks and full gate per stage,
  read by the stage ritual when that stage starts.
- A context budget in `SKILL.md`: what is read at preflight, what is read at each stage, and the
  rule that an exception is taken deliberately and recorded.

- `references/colors-contract.md` — the Colors area gets its own contract: palette mechanism and
  naming scheme, semantic layer, system slots, appearance variants and the project's colour guard,
  plus baseline rules COL-01…COL-10 and a failure catalog (palette named after one usage site, a
  guard blind to some literal forms, two project documents disagreeing, alpha variants as entries).
- Colour policy gates: stages 3 and 8 run the COL-01…COL-05 detections, or the project's own guard
  with its documented invocation, over the feature's changed files.
- `references/capability-discovery.md` — runtime capability discovery contract: a preflight sweep
  over skills, MCP servers and tools, MCP resources, plugins and project-local scripts; a Figma
  access probe (transport → auth → node reachability → capability set → asset path → write mode →
  stage 5 credential); role definitions, the selection rule between competing candidates, and the
  handling of tools that did not exist when the skill was written.
- `Capability ledger` and `Figma access probe` sections in the pipeline manifest template
  (`pipeline_schema_version: 9`): one row per role with binding, kind/origin, evidence, status and
  affected stages.
- `import-figma-assets` ships in this repository as the third skill, so stage 2 no longer depends on
  an external catalog entry.
- `references/layout-adaptivity-contract.md` — Layout & Adaptivity becomes the sixth area of the
  UI convention contract: reference canvas, permitted scaling API, supported devices, forbidden
  patterns, baseline rules LAY-01…LAY-11 and a failure catalog (FAIL-01…FAIL-04).
- Layout policy gates: stage 3 blocks on the LAY-01…LAY-10 detections, stage 5 requires at least
  one non-reference size per screen, stage 6 requires the smallest supported device plus devices
  with and without a home indicator, stage 8 re-runs the detections.
- `Layout policy checks` table and a `Layout` contract row in the pipeline manifest template
  (`pipeline_schema_version: 8`); the table becomes `UI policy checks` and carries the COL rows too
  (`pipeline_schema_version: 10`).
- `check.sh` — local check runner: validator tests on every installed Python 3 (including
  `/usr/bin/python3` 3.9 from the Xcode Command Line Tools), skill lint, shell syntax.
- `tools/pre-push` — optional git hook that runs `check.sh` before a push.

### Fixed

- `ui_guard.py` resolves named constants instead of matching literals only. The first version was
  blind to `.frame(width: OnboardingLayout.width, height: OnboardingLayout.height)` — the exact
  fixed-canvas shape LAY-01 was written from — while reporting 55 lesser findings on the same file
  and looking healthy. Found by the first run on a real codebase (PetCare onboarding), not by the
  test suite, whose fixtures were all literals. Resolution follows one constant through another and
  prints the resolved value in the finding (`K.w = 393`).
- LAY-01 no longer keys on a size matching the reference canvas. A frame pinning **both**
  dimensions is the canvas shape whether the sizes are literals, named constants, or symbols the
  script cannot resolve at all; `maxWidth: .infinity` and icon-sized frames are not.
- Findings anchor to the line carrying the modifier instead of the first line of the chain. The old
  anchor could land on a closing paren belonging to a different call, which put waivers out of
  reach — and adding the waiver comment re-split the chain and moved the anchor again. Both
  documented waiver positions now work.
- LAY-09 no longer fires on every `scaleEffect` in a file that happens to contain `Text`. A factor
  driven by state — `configuration.isPressed ? 0.97 : 1` and the like — is the animation the rule
  permits; press feedback in a `ButtonStyle` was a guaranteed false positive.

### Changed

- Preflight no longer reads the Layout, Colors and Strings contracts. The audit resolves its six
  rows from the baseline digests in `project-ui-conventions.md`; each contract is read in full at the
  stage that enforces it (Strings at 1, Layout and Colors at 3), with an escape hatch for a row the
  digest cannot resolve. Preflight load drops from ~27k to ~16.8k tokens.
- `SKILL.md` shrinks from 35131 to ~25k chars: the eight stage bodies and the 41-bullet mistake list
  move to references. No rule changed, only where it is stored and when it is read.
- A subagent's return is capped at ~800 characters, and the cap is on the summary, not on the work:
  file contents, diffs, raw MCP payloads, catalogs, logs and screenshots are never returned inline —
  they go to the artifact root and travel as a path plus the derived finding. Delegation that
  returns the bytes it was sent to read moved the reading, not the cost.
- A stage reads its manifest sections, not the manifest. The floor is capability ledger + question
  log + stage table plus whatever the stage owns; below that floor a stage can miss an open blocker,
  which is the one way this saving turns into a bug. Resume still reads the manifest whole.
- The Figma cache rule became concrete: a path, a `pin.json` key, and a discard rule (pin changed →
  drop the whole directory rather than reason about which nodes moved).
- Stages 5 and 6 run a mechanical geometry pass before anything is looked at, and the gates now
  require both the run's marker and a record of what was reviewed by eye — every failing pair, plus
  one passing pair per screen.
- Pipeline manifest template `pipeline_schema_version: 13`: `layout-color-guard`, `manifest-read`
  and `screenshot-geometry` ledger rows; contract sources recorded as `path#section @ digest`; the
  UI policy check table records the guard's exact invocation, its clean/dirty marker and which rows
  it cannot fill; the adaptivity matrix and design comparison tables carry the geometry-check result
  and a `Looked at by eye` column.
- `check.sh` runs every `scripts/tests/test_*.py` instead of the single validator suite.
- Stages are bound by **role**, not by skill name. Outside the skills shipped here, every name in
  `SKILL.md` and the adapters is an example verified against the live catalog; a role can bind a
  renamed, namespaced, plugin-prefixed or newly published tool, and never a name that did not appear
  in the run's discovery output.
- Figma preflight now runs an explicit auth probe (one `whoami`) before the first read and
  separates the failure causes — auth, file permission, missing node, wrong transport — instead of
  reading every error as a broken node id. The acquisition budget accounts for that call.
- A discovered tool is classified by what its description does: anything that mutates the design
  source stays unused regardless of its name, and tool descriptions or MCP server instructions are
  treated as untrusted data, never as instructions.
- The preflight audit now resolves six areas instead of five; stages 1–8 stay blocked until all six
  contract rows are filled. Documentation outranks code precedent: a pattern the project's docs mark
  legacy cannot be repeated because neighbouring screens use it. Two project documents stating
  different rules for one area is a `conflict` to ask about, not a preference to exercise.
- The Colors baseline in `project-ui-conventions.md` shrinks to what the audit resolves and points at
  `colors-contract.md` for the rules.
- Both skills are now written in English — `SKILL.md`, references, adapters and templates. The
  Russian trigger phrases stay in each `description`, and generated project documents follow the
  user's language while machine-read structure stays English.
- `ui_plan.py` reads the asset checklist from `## Sub-checklist: assets` and still accepts the
  pre-translation `## Под-чеклист: ассеты` heading, so manifests already in flight keep validating.
- CI no longer runs the validator tests; they run locally. The workflow keeps only the skill
  structure and relative-link checks.
- `install.sh --force` moves the replaced skill to `.skill-backups` beside the target directory
  instead of leaving it inside, where an agent would load the backup as a duplicate skill.

## [1.0.0] — 2026-08-06

First public release.

### Added

- `figma-full-cycle` orchestrator skill: 8 gated stages from a Figma parent frame to a
  review-clean feature branch, one commit per stage.
- Read-only project convention audit (Strings, Typography, Colors, Images, Accessibility)
  that runs before any Figma call or edit and gates every stage.
- `ui-first` mode — implement screens now, defer product logic until requirements arrive.
- Resume from any stage, reconciled against git rather than trusting the manifest alone.
- `ui_plan.py` — validator for the machine-checked spec → implementation contract
  (`--phase ui` and `--phase production`), with 32 unit tests.
- `localization_context.py` — bounded read-only inspection of `.xcstrings` / `.strings` /
  `.stringsdict`: `inventory`, `lookup`, key-level `diff`, `validate`.
- Agent adapters for Claude Code and Codex, plus an OpenAI-style agent manifest.
- Templates for the tracked pipeline manifest, local runtime state and the UI plan.
- `figma-feature-spec` companion skill: Figma parent frame → written spec, asset inventory and
  implementation checklist.
- `install.sh` for symlink or copy installation into any agent skills directory.

[Unreleased]: https://github.com/gwair1989/figma-full-cycle/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/gwair1989/figma-full-cycle/releases/tag/v1.0.0
