# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `check.sh` — local check runner: validator tests on every installed Python 3 (including
  `/usr/bin/python3` 3.9 from the Xcode Command Line Tools), skill lint, shell syntax.
- `tools/pre-push` — optional git hook that runs `check.sh` before a push.

### Changed

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
