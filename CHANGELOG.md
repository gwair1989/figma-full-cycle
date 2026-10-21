# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Device Usage now defines a focused check for one UI change, optional native hierarchy/hit-point
  targeting, and exclusive input ownership when agents share a physical target. Device Hub stays
  primary, iPhone Mirroring stays the fallback; subagents and Xcode MCP are not prerequisites.
- Device Usage reports observation categories separately from route status and coverage. Its
  route table now includes observation/category and all four scroll directions.
- Horizontal scrolling guidance now separates contact drag from indirect scroll, bounds carousel
  overshoot retries, and checks whether the active API can express horizontal input or held
  Shift plus scroll in Mirroring.
- Removed links to the former `gwair1989/device-usage` repository after its deletion. All four
  skills continue to be maintained here, with independent Device Usage installation preserved.

## [1.1.0] — 2026-10-19

### Added

- This repository is now the canonical development and release location for all four skills.
  Device Usage remains independently installable; its original repository is retained for history.
- A four-skill Codex plugin package: portable `plugin.json`, a Codex compatibility manifest and a
  repo marketplace. Each skill remains separately invocable and available as a standalone directory.
- Bundled `device-usage` from `gwair1989/device-usage` at
  `8d471d565b3335969e5d90b1eac22f67f237b5e1`, including its MIT notice, references, optional Node
  screenshot recorder and tests. The original checkout is not a runtime dependency. Its agent
  compatibility notes now account for this bundle's namespace.
- Optional `physical-device-control` role for requested Device Hub checks in stages 5–7, with
  reviewed native screenshot evidence and route coverage separate from the simulator matrix.
  Pipeline schema 15 adds physical-device results; hardware identifiers remain in local runtime.
- Repeatable `install.sh --skill NAME` selection. Installing the full cycle includes its two
  required companions; selected uninstall preserves shared companions. Package and installer tests
  and the device recorder tests run in `check.sh` and CI.
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

### Added

- LAY-04 gets a fixed-size composition exception, declared once above the block:
  `// ui-guard: composition <name> — <reason>`. A group of elements forming one piece of artwork,
  sized in the design and anchored natively by its parent, places its parts against each other and
  not against the screen — the allowance LAY-03 already makes for a single fixed element, applied to
  a group. The marker covers the block and the modifiers chained onto it, so one comment replaces a
  waiver per element; a rule costing a waiver per element teaches people to waive without reading.
  Refused when the block's frame is screen-sized, which would otherwise license the fixed-canvas
  pattern one comment at a time. Every exemption is printed with its name and lines.
- `screenshot_diff.py --grid-map` prints which cells differ as text. `44% of cells differ` does not
  say whether the screen shifted, lost its bottom or drifted on one side, and finding out otherwise
  meant opening the images — the cost the script exists to avoid. The map is always in the JSON
  report.

### Fixed

- A `.frame(...)` written across several lines was not read at all. The chain broke at the opening
  paren, so nothing inside the call was ever seen: identical code produced four findings on one line
  and none across four. A miss for LAY-02 and LAY-03 everywhere, not just inside a composition that
  then could not suppress what was never found.
- `.frame(width: proxy.size.width, height: proxy.size.height)` inside a `GeometryReader` no longer
  reads as a canvas. It means "fill whatever the parent offers" — the opposite of a fixed artboard —
  and the idiom was flagged everywhere it appeared.
- LAY-01 reports the frame directly above the `scaleEffect` rather than the first one in the type.
  A correct alarm pointing at the wrong frame sends the fix to the wrong place.
- `ui_guard.py constants` prints a `CGSize` as `381×373.85` instead of `—`. It resolves fine through
  its members; the legend beside `—` says the resolver could not read it, which was untrue for every
  size constant in a project.
- LAY-01 stopped inventing canvases. Three faults, all found by the third run on real code: the
  "provably smaller" exoneration demanded *both* sides resolve, so any adaptive width computed from
  live geometry made a 280pt-tall card look like an artboard; the scaleEffect and the frame were
  paired anywhere in the file, so a `ButtonStyle` and a card two declarations away became one screen;
  and the factor was never checked, so `isPressed ? 0.97 : 1` — the exact shape LAY-09 had already
  learned to skip — counted as scaling. Now: one readable small side disproves a canvas, the pair
  must share a type body, and only a static factor qualifies.
- The composition marker's reach ended at the first line of a multi-line call, so a block whose own
  `.frame(...)` spanned lines lost the modifiers after it — 9 findings suppressed when written on
  one line, 6 when written across four.
- A `typealias` now resolves to the type it names. Two neighbouring files with the same fixed canvas
  reported 9 findings and 1, purely because one spelled the type out and the other used
  `private typealias Layout = …`.
- Resolved values print with enough digits to match the declaration; 578.2218 was shown as 578.222.
- A qualified constant reference no longer borrows an unrelated one. With a single table for the
  whole run, `Multi.canvas.height` matched a bare `height` declared in another type entirely — a
  wrong number printed in a finding, and a wrong number deciding whether a frame was smaller than
  the screen. It went unnoticed because every fixture so far used the same 393×852 on both sides.
  Suffix matching now stops at two components, and a recognised `.width`/`.height` access resolves
  through its own base or not at all.
- Constant resolution covers the declaration forms a project actually writes, enumerated rather than
  guessed at: literals, one-line `enum`s, multi-line declarations, computed properties (single and
  multi-line, with or without `return`), `as` casts, any `Type(width:height:)` and not only `CGSize`,
  and one constant naming another. A test matrix asserts all nine reach LAY-01 and LAY-03, each with
  a distinct value so a leaked one shows as a wrong number instead of an accidental pass.
- New `ui_guard.py constants` prints what the resolver read, marking anything it cannot read with
  `—`. Every gap found so far was a declaration form nobody could see failing; this turns the next
  one into a command instead of a bisection over fixtures.
- Constant resolution reaches the shapes a real project uses. The first version read literals in a
  single file, so it stayed silent on `OnboardingLayout.width = GeometryData.referenceCanvasSize.width`
  — layout constants in their own file, behind a `CGSize` — which is the canonical FAIL-01 case and
  the convention the contract tells projects to follow. Resolution now spans every file in the run,
  reads `CGSize(width:height:)` members, and collects declarations written on one line inside an
  `enum`.
- `--reference-canvas`, documented as sharpening LAY-01, switched it off. The unresolved-size
  fallback was gated on *no* canvas being supplied, so passing the flag disabled the very rule it
  was meant to sharpen — and the test covering that fallback passed only because it omitted the
  flag. A pinned frame is now judged canvas unless provably smaller than the screen, with or without
  the flag.
- The composition exemption was wrong in both directions: it refused a 381×373 illustration on a
  393pt canvas while honouring a real 393×852 canvas whose size came from a `CGSize` constant —
  legalising a fixed canvas one comment at a time. The check now compares against the reference
  canvas (artwork is under 90% of it in at least one dimension) instead of a flat 300pt threshold,
  and fails closed on a size it cannot read.
- A composition also suspends LAY-02 and LAY-03 inside itself, including on the frame declaring its
  own size. Fixed geometry is what artwork is made of; flagging an illustration for stating its
  dimensions is the same mistake as flagging its internal offsets.
- A composition marker that exempts nothing now says so instead of vanishing, so a stale marker
  cannot rot in the source; a refused one is not also reported as empty.
- A cross-aspect `PASS` from `screenshot_diff.py` carries `bottom band not gated — check content
  clipping by eye`. A bare PASS read as "all good" exactly where clipping had deliberately not been
  judged.
- `--max-findings` has a help string, `--reference-canvas` describes what it actually changes, and
  LAY-04's message points at the composition marker rather than only at waivers.
- Both scripts document their exit codes, their `*_CLEAN` / `*_DIRTY` stdout markers and their source
  annotations in `--help` — on the subcommand, where they are actually read. The truncation notice
  now names `--max-findings` and `--format json` instead of leaving the reader to guess.
- `screenshot_diff.py` no longer gates on the grid diff across device classes. Normalizing stretches
  the mock anisotropically while a native layout adapts by holding its metrics in points, so a
  correctly adapted screen diverges from the stretched mock exactly as a broken one does — measured
  at 41% on a content-dense fixture that is entirely correct, against a real screen's 44%. Beyond
  `--aspect-tolerance` (default 2%) the grid and the bottom-band count are reported and not gated,
  and the verdict rests on letterbox, pillarbox and background-to-the-edge. Clipping on a smaller
  device is now explicitly a reviewer question; stages 5 and 6 require eyes on the smallest-device
  row whatever its verdict, and the claim that the script answers all four LAY-11 questions has been
  corrected everywhere it appeared.
- Test fixtures for `screenshot_diff.py` were all proportional scales of the mock — that is, models
  of the fixed-canvas defect rather than of the fix, which is why 21 green tests missed the above.
  Added `native_rows`, which keeps insets, gaps and row heights fixed in points as the canvas
  changes, and a same-aspect render size so the gated and ungated paths are both covered.
- Failing pairs now name the suspect edge bands and their widths in the text output. An asymmetric
  pillarbox (85px against 49px) is a strong signal that previously appeared only in the JSON.
- The alpha-channel note no longer tells the author to re-export a simulator capture from Figma.
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
- "Driven by state" now includes the shape that does not announce itself. The previous test read the
  expression for a ternary, a comparison or an animation keyword, which misses the collapsing header:
  `.scaleEffect(1 - avatarProgress * 0.2)`, where `avatarProgress` derives from an `@State` scroll
  offset written on every frame by `.onScrollGeometryChange`, is plain arithmetic and read as a
  constant. The guard now follows the factor to its declaration — a property carrying `@State`,
  `@Binding`, `@GestureState`, an observed store and the rest, reached through however many computed
  properties — and treats it as the animation LAY-09 permits. Two false positives in PetCare, both on
  the same idiom copied between screens; the neighbouring `.offset(y: -avatarProgress * 24)` had
  always been silent, because LAY-04 asks what the value resolves to rather than what keywords it
  contains. A symbol that is never declared as state stays static, so `.scaleEffect(canvasScale)` and
  `min(w / 393, h / 852)` over text remain findings and LAY-01 is untouched.

### Changed

- Removed the TCA default from the full cycle, adapters, stage instructions, spec template and
  READMEs. Preflight now resolves the feature's architecture from project documentation or an
  explicit user decision; missing, ambiguous or contradictory documentation requires a user
  answer, including in `ui-first`. Source code and installed skills cannot select the architecture.
  Stage 3 builds the chosen architecture's UI/state interfaces; stage 7 implements business logic
  through them. Standalone `figma-feature-spec` follows the same rule.
- Pipeline manifest template `pipeline_schema_version: 14`: adds a Project architecture contract
  with the selected architecture, scope, source and integration boundaries. Resume resolves missing
  contracts in older manifests and invalidates dependent evidence when the decision changes.
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

[Unreleased]: https://github.com/gwair1989/figma-full-cycle/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/gwair1989/figma-full-cycle/releases/tag/v1.1.0
[1.0.0]: https://github.com/gwair1989/figma-full-cycle/releases/tag/v1.0.0
