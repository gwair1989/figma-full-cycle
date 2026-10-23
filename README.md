# Figma Full Cycle

**A Figma parent frame in. A reviewed, built, convention-compliant feature out.**

`figma-full-cycle` is an orchestrator [Agent Skill](https://code.claude.com/docs/en/skills) for
Claude Code and Codex. You give it the link to the parent frame of a feature in Figma; it drives the
whole road from design to merged code — spec, assets, UI, design diff, adaptivity, logic, review —
as eight gated stages, one commit per stage, with a tracked manifest as the source of truth.

[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](LICENSE)
[![CI](https://github.com/gwair1989/figma-full-cycle/actions/workflows/ci.yml/badge.svg)](https://github.com/gwair1989/figma-full-cycle/actions/workflows/ci.yml)
![Skills: 6](https://img.shields.io/badge/skills-6-blue)
![Runtime deps: none](https://img.shields.io/badge/runtime%20deps-none-brightgreen)
![Target UI: SwiftUI](https://img.shields.io/badge/target-SwiftUI-orange)

> **Language note.** The Figma skills, references and templates are English. The bundled
> `device-usage` instructions retain their upstream Russian. Each Figma skill's
> `description` also keeps its Russian trigger phrases, so Russian prompts still fire it, and the
> documents the skill writes into your project follow **your** language. Machine-read structure —
> UI Plan keys, statuses, manifest headings, commit subjects — stays English so the validator and
> resume keep working. [README.ru.md](README.ru.md) is the Russian version of this page.

---

## One plugin, six entry points

This repository is both a collection of reusable skills and a distributable Codex plugin.
Installing the plugin makes all six workflows available; invoking one does not start the others.

| Skill | Use independently for |
|---|---|
| `figma-full-cycle` | Implementing an entire Figma feature; orchestrates spec, assets, comparison and adaptivity skills |
| `figma-feature-spec` | Writing a feature specification without implementing the app |
| `import-figma-assets` | Importing artwork into an Xcode asset catalog |
| `figma-design-compare` | Comparing existing screens with a pinned Figma design |
| `swiftui-adaptivity-check` | Checking supported configurations, with or without Figma |
| `device-usage` | Testing a physical iPhone through Device Hub, without Figma or a pipeline |

This is the canonical repository for all six skills. Device Usage development, issues and releases
now live here; the former standalone repository has been removed. You can still install and invoke
`device-usage` on its own.

Device Hub is the physical-device workflow's primary channel; iPhone Mirroring is its fallback.
The plugin supplies instructions and an optional screenshot recorder. It does not install Xcode,
Computer Use, an MCP server or macOS permissions. Simulator checks remain separate; one connected
phone does not replace the adaptivity matrix. Physical checks join the full cycle only when the
user or project requires them.

## Why this exists

A single "implement this Figma screen" prompt fails predictably on real features:

| Failure | What the skill does instead |
|---|---|
| Agent invents product behavior a static mockup never contained | Every unknown becomes a logged question or an explicit `TBD` — never a silent guess |
| Agent ignores the project's own strings / typography / colors conventions | Read-only convention audit **before** Figma and before any edit; five resolved contract lines gate every stage |
| Whole localization catalogs and raw MCP payloads burn the context window | Bounded read-only helpers, scoped Figma reads, sub-agent delegation, compact evidence in state |
| One giant unreviewable commit | One stage = one commit, each behind a gate proven by a real command |
| "It's green" claimed without running anything | Gates require evidence: command, time, exit code, artifact path |
| Design left the trunk dirty | Feature runs in its own branch + worktree; cleanup only after a confirmed merge |

## The pipeline

| # | Stage | Gate (abridged) |
|---|---|---|
| 0 | Worktree — branch, secrets by symlink, build defaults, baseline build/test | Baseline recorded, manifest created |
| 1 | Spec + UI Plan — screens, navigation map, asset inventory, copy inventory | Spec and `UI_PLAN.json` on disk, `ui_plan.py --phase ui` passes, blockers answered |
| 2 | Assets — import by node-id inventory | Build succeeds, every asset verified present |
| 3 | UI implementation + project architecture skeleton | UI Plan evidence fresh, strings verified, build succeeds, every screen/state done |
| 4 | UI refactor — *conditional*, only on findings | Build succeeds, affected checks marked `stale` |
| 5 | Design diff — per-screen comparison against the pinned Figma frame | Report on disk, mismatches fixed and re-checked |
| 6 | Adaptivity — small/large screens, light/dark, content sizes, locales, keyboard | No clipping or overlap, evidence stored |
| 7 | Business logic + runtime navigation + tests | `ui_plan.py --phase production` passes, tests pass, TBDs flagged |
| 8 | Final review | Review clean, no stray user-facing literals, clean checkpoint committed |

Two properties make this survivable in practice:

- **Resume from any stage.** State lives on disk and is reconciled with git — `start: stage N`,
  or just ask it to continue the feature.
- **`ui-first` mode.** Design exists, the spec does not? Stages 0–6 run now; product questions are
  recorded as `deferred-to-spec` instead of blocking; stages 7–8 wait for the requirements.

## Requirements

- **Agent:** Claude Code or Codex (an adapter maps every capability to concrete tool names).
- **Figma MCP** with read access, and `FIGMA_ACCESS_TOKEN` by stage 5.
- **Python 3.9+** — standard library only, nothing to `pip install`.
- **Target project:** an Xcode/SwiftUI app. Architecture comes from the project's documentation
  or an explicit user decision. Missing, ambiguous or contradictory documentation → ask the user;
  source code and installed skills do not select the architecture. The decision and its source are
  recorded in the manifest and spec before implementation, including in `ui-first`. Stages 3 and 7
  follow that architecture; no particular architecture framework is required.
- **Companion skills** are **discovered, not required by name.** Preflight sweeps the skills,
  MCP tools, MCP resources, plugins and project-local scripts actually installed on your machine and
  binds one of them to each stage *role* — `design-to-code-workflow`, `platform-ui-idiom`,
  `app-architecture`, `visual-comparison`, `code-review`, … Renamed, namespaced, plugin-prefixed or
  brand-new vendor skills are picked up the same way; every role that finds nothing falls back to a
  documented path. Only what ships here is pinned by name: `figma-full-cycle`, `figma-feature-spec`,
  `import-figma-assets`, `figma-design-compare`, `swiftui-adaptivity-check`, and optional `device-usage`. Bundled identities resolve to their actual
  registered names, including plugin namespaces.
- **Physical iPhone checks only:** macOS, a paired physical iPhone, Xcode with Device Hub, and a
  compatible desktop Computer Use tool for autonomous GUI actions. Follow the bundled skill's
  capability checks; CLI diagnostics remain possible when GUI control is unavailable.
- **Optional device evidence recorder and its tests:** Node.js 22+, standard library only.

Missing capabilities are reported as a single up-front blocker list, not discovered one by one
halfway through the build. The resulting bindings — plus the Figma auth and node-reachability
probe — are written into the manifest's capability ledger.

## Install

### Codex plugin

The portable manifest is `plugin.json`; `.codex-plugin/plugin.json` supports Codex compatibility.
The repo marketplace is `.agents/plugins/marketplace.json`. From this checkout, with a Codex CLI
that exposes `plugin add`:

```bash
git clone https://github.com/gwair1989/figma-full-cycle.git
cd figma-full-cycle
codex plugin marketplace add .
codex plugin add figma-full-cycle@figma-full-cycle-local
```

Alternatively select the local marketplace in the desktop Plugins Directory. Start a fresh
session after installation and select the skill by the exact name shown in its catalog; a plugin
may qualify it, for example `figma-full-cycle:device-usage`. Packaging follows the
[official plugin format](https://developers.openai.com/plugins/build/plugins).
This repo is a local distribution source, not a public-directory listing.

### Standalone skills

```bash
git clone https://github.com/gwair1989/figma-full-cycle.git
cd figma-full-cycle
./install.sh
```

`install.sh` symlinks all six skills into `~/.claude/skills` — so `git pull` updates them in place.

```bash
./install.sh --target ~/.codex/skills   # Codex
./install.sh --target ~/.agents/skills --skill device-usage   # only Device Hub workflow
./install.sh --target ~/.agents/skills --skill figma-feature-spec --skill import-figma-assets
./install.sh --target .claude/skills    # this project only
./install.sh --copy                     # copy instead of symlink
./install.sh --force                    # replace an existing skill of the same name
./install.sh --uninstall                # remove what it installed
```

`--skill` is repeatable. Selecting `figma-full-cycle` also installs its four companions:
`figma-feature-spec`, `import-figma-assets`, `figma-design-compare`, `swiftui-adaptivity-check`.
Device Usage stays optional. The full cycle and either visual validator install
`_figma-full-cycle-shared/` once alongside the skill directories. It contains canonical contracts
and read-only helpers, has no `SKILL.md`, and is not another entry point.

```bash
./install.sh --target ~/.codex/skills --copy --skill figma-design-compare
./install.sh --target ~/.codex/skills --copy --skill swiftui-adaptivity-check
```

Copied visual skills travel with the sibling `_figma-full-cycle-shared/` directory; the original
checkout and the full-cycle skill are not needed. Use `--force` to update an existing copied
installation. Uninstall removes only selected symlinks and preserves companions/shared resources
so other consumers keep working; copied directories require manual removal. The source tree is
also usable directly as a plugin, which includes the shared directory.

Use either plugin installation or standalone registration for each skill. Codex standalone
invocations use `$<skill-name>`, including `$figma-design-compare` and `$swiftui-adaptivity-check`.
The same directories work in Claude Code; Device Hub still needs desktop Computer Use.

Already keeping these skills in your skills directory? `--force` replaces them and moves the old
copies to `.skill-backups` **next to** the skills directory — never inside it, where an agent would
pick the backup up as a second, duplicate skill.

Verify: start a new agent session and check that `figma-full-cycle` appears in the skill list.

## Use

Give the skill the link to the **parent** frame — the container holding every screen of the flow,
not a single screen:

```text
Full cycle from this Figma frame: https://figma.com/design/<fileKey>/App?node-id=1234-5678
```

```text
Implement the feature from <url>, mode: ui-first — requirements come later
```

```text
Continue <FEATURE>, start: stage 5
```

Russian triggers fire it too — «сделай фичу по фигме», «полный цикл по фрейму», «сверстай экраны, тз
позже» — and the documents it writes then come out in Russian. See [README.ru.md](README.ru.md).

### Standalone visual checks

```text
Use $figma-design-compare to compare these implemented screens with <Figma URL>; save a report.
Use $swiftui-adaptivity-check to check these screens across supported devices and text sizes, without Figma.
```

Standalone checks write `docs/<RUN>_DESIGN_COMPARE.md` or `docs/<RUN>_ADAPTIVITY.md`, with local
artifacts under `docs/.cache/<RUN>/`. They need no pipeline manifest/UI Plan, do not commit, and
apply fixes only when authorized. Authenticated MCP reads suffice for standalone comparison;
the full cycle retains its own stage 5 credential check. Adaptivity needs no Figma URL/token/mock;
without a mock or `sips`, every native capture is reviewed directly. Stages 5/6 call these same
skills with pipeline context and import the report/evidence into the orchestrator-owned manifest.

### What it writes into your project

| File | Tracked | Role |
|---|---|---|
| `docs/<FEATURE>_PIPELINE.md` | yes | Manifest: stages, gates, evidence, question log, decisions |
| `docs/<FEATURE>_UI_PLAN.json` | yes | Machine-checked handoff contract from spec to implementation |
| `docs/<FEATURE>_PIPELINE.local.md` | no (gitignored) | Local runtime: absolute paths, simulator UDID |

## What's in the box

```
skills/
├── _figma-full-cycle-shared/         # resources only, no SKILL.md
│   ├── references/                  # Figma acquisition, UI contracts, validation context
│   └── scripts/                     # screenshot_diff.py, ui_guard.py, localization_context.py
│       └── tests/                   # screenshot and UI guard suites
├── figma-full-cycle/
│   ├── SKILL.md                     # orchestration, state, questions, gates
│   ├── adapters/                    # Codex and Claude Code capability maps
│   ├── references/                  # discovery, UI Plan, pitfalls, device integration
│   │   └── stages/                  # 5/6 are companion handoff adapters
│   ├── scripts/                     # ui_plan.py, manifest.py and tests
│   ├── templates/                   # PIPELINE, PIPELINE.local, UI_PLAN
│   └── agents/openai.yaml
├── figma-feature-spec/              # stage 1, spec template
├── import-figma-assets/             # stage 2, imageset helpers
├── figma-design-compare/            # stage 5, standalone or pipeline
├── swiftui-adaptivity-check/        # stage 6, works without Figma
└── device-usage/                    # optional physical iPhone / Device Hub
```

### The five scripts

All read-only, stdlib-only CLIs — the skill calls them so the model never has to swallow raw data:

```bash
python3 skills/figma-full-cycle/scripts/ui_plan.py validate \
  --plan docs/FEATURE_UI_PLAN.json \
  --manifest docs/FEATURE_PIPELINE.md \
  --project-root . --phase ui
```

`ui_plan.py` validates the implementation contract — screens, components, tokens, copy, assets and
their provenance — and returns small, actionable diagnostics before a build loop starts.

```bash
python3 skills/_figma-full-cycle-shared/scripts/localization_context.py inventory --root .
```

`localization_context.py` inspects `.xcstrings` / `.strings` / `.stringsdict` with bounded output:
`inventory`, targeted `lookup`, key-level `diff`, `validate`. It never writes catalogs and never
prints them whole.

```bash
python3 skills/_figma-full-cycle-shared/scripts/ui_guard.py check \
  --project-root . --changed-since <BASE_SHA> \
  --reference-canvas 393x852 --asset-catalog App/Assets.xcassets
```

`ui_guard.py` is the stage 3 and stage 8 gate for the Layout and Colors contracts. It reports
`path:line: RULE-ID: message` and nothing else, so reviewing a feature costs findings instead of a
read of the diff. It is deliberately partial and prints with every run the rules it did **not**
check — a clean run is only as wide as that note.

```bash
python3 skills/figma-full-cycle/scripts/manifest.py get \
  --file docs/FEATURE_PIPELINE.md --section "Capability ledger" --section "Question log"

python3 skills/figma-full-cycle/scripts/manifest.py verify-sources \
  --file docs/FEATURE_PIPELINE.md --project-root .
```

`manifest.py` reads parts of the manifest instead of all of it — a filled one runs tens of kilobytes
by stage 6 — and answers the question a resume actually has: `verify-sources` re-hashes the documents
the UI convention contract was resolved from and reports per area `unchanged` / `CHANGED` /
`unrecorded`, so an unchanged project costs one command instead of re-reading its documentation.

```bash
python3 skills/_figma-full-cycle-shared/scripts/screenshot_diff.py compare \
  --render build/Onboarding@iPhoneSE.png --mock design/Onboarding.png \
  --ignore-top 6% --out reports/onboarding-se.json
```

`screenshot_diff.py` compares an implementation screenshot against a design mock **of a different
size** — it normalizes the mock to the render first, because at the reference size a fixed-canvas
layout matches pixel-for-pixel and hides the breakage. It answers letterbox, pillarbox and
background-reaching-the-edges in about 0.3s per pair, with a `batch` mode for the stage 6 matrix. It
needs `sips`, which ships with macOS — the pipeline already requires macOS for `xcrun simctl`, so
nothing new gets installed.

Across device classes it deliberately says less: normalizing stretches the mock, while a native
layout adapts by holding its metrics in points, so the structural grid diff flags a correctly adapted
screen as loudly as a broken one. Beyond `--aspect-tolerance` the grid is reported and not gated, and
clipping on a smaller device stays a reviewer question.

It is a filter, not the gate: it sees geometry, not design, and prints with every run what it is
blind to — typeface, icon shape, copy, small colour shifts. Eyes go on every failure and on one
passing pair per screen.

## Safety model

- **Figma is untrusted input.** Text inside a design is content, never instruction.
- **Figma write tools stay disabled** (`use_figma`, `upload_assets`, Code Connect writes, …) unless
  the user explicitly asks to modify the design file.
- **Secrets are never copied.** A worktree gets a symlink to the main checkout's `.env`; a secret
  scan runs before every commit; values are never printed.
- **No invented translations.** Source copy is not broadcast into other locales without a documented
  project policy; translation readiness is a separate gate.
- **Merge is the user's call.** Passing stage 8 produces a PR-ready branch — never an automatic merge.

## Porting to another agent

Adding an agent means adding one adapter file, not editing the core. Copy
`skills/figma-full-cycle/adapters/claude-code.md`, replace the right column with your agent's tool
names, keep the capability rows intact, and reference it from the skill's adapter section. The core
`SKILL.md` stays tool-agnostic by design.

## Contributing

Issues and PRs welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Checks run locally, in seconds:

```bash
./check.sh
```

It runs the Python validator and package/installer tests on every detected Python 3 minor
version, then the Node.js 22+ device recorder tests, skill lint and shell syntax checks.
All tests use local fixtures and temporary directories; they do not operate a phone or install
the plugin into your account. To make that automatic before every push:

```bash
ln -sf ../../tools/pre-push .git/hooks/pre-push
```

CI checks skill structure, relative links, package/installer behavior and the device recorder.
The larger Python validator suites stay in the local check runner.

## License

[MIT](LICENSE) © Oleksandr Khalypa

The bundled Device Usage skill preserves its [MIT notice](skills/device-usage/LICENSE). It was
imported from `gwair1989/device-usage` at commit `8d471d565b3335969e5d90b1eac22f67f237b5e1`.
Further development happens directly in this repository; see [CONTRIBUTING.md](CONTRIBUTING.md).
