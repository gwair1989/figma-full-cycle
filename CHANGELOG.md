# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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

### Changed

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
