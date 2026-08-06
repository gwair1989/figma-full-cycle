# Figma Full Cycle

**A Figma parent frame in. A reviewed, built, convention-compliant feature out.**

`figma-full-cycle` is an orchestrator [Agent Skill](https://code.claude.com/docs/en/skills) for
Claude Code and Codex. You give it the link to the parent frame of a feature in Figma; it drives the
whole road from design to merged code — spec, assets, UI, design diff, adaptivity, logic, review —
as eight gated stages, one commit per stage, with a tracked manifest as the source of truth.

[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](LICENSE)
[![CI](https://github.com/gwair1989/figma-full-cycle/actions/workflows/ci.yml/badge.svg)](https://github.com/gwair1989/figma-full-cycle/actions/workflows/ci.yml)
![Skills: 2](https://img.shields.io/badge/skills-2-blue)
![Runtime deps: none](https://img.shields.io/badge/runtime%20deps-none-brightgreen)
![Target stack: SwiftUI + TCA](https://img.shields.io/badge/target-SwiftUI%20%2B%20TCA-orange)

> **Language note.** The skill instructions and the documents it produces are written in Russian —
> that is the working language of the pipeline. The repository docs are bilingual:
> [README.ru.md](README.ru.md) is the Russian version of this page.

---

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
| 3 | UI implementation + TCA skeleton | UI Plan evidence fresh, strings verified, build succeeds, every screen/state done |
| 4 | UI refactor — *conditional*, only on findings | Build succeeds, affected checks marked `stale` |
| 5 | Design diff — per-screen comparison against the pinned Figma frame | Report on disk, mismatches fixed and re-checked |
| 6 | Adaptivity — small/large screens, light/dark, content sizes, locales, keyboard | No clipping or overlap, evidence stored |
| 7 | Reducer logic + runtime navigation + tests | `ui_plan.py --phase production` passes, tests pass, TBDs flagged |
| 8 | Final review | Review clean, no stray user-facing literals, clean checkpoint committed |

Two properties make this survivable in practice:

- **Resume from any stage.** State lives on disk and is reconciled with git — `старт: этап N`,
  or just ask it to continue the feature.
- **`ui-first` mode.** Design exists, the spec does not? Stages 0–6 run now; product questions are
  recorded as `deferred-to-spec` instead of blocking; stages 7–8 wait for the requirements.

## Requirements

- **Agent:** Claude Code or Codex (an adapter maps every capability to concrete tool names).
- **Figma MCP** with read access, and `FIGMA_ACCESS_TOKEN` by stage 5.
- **Python 3.9+** — standard library only, nothing to `pip install`.
- **Target project:** an Xcode/SwiftUI app; stage 3 and stage 7 assume
  [TCA](https://github.com/pointfreeco/swift-composable-architecture), with documented fallbacks
  to the project's own stack skills.
- **Companion skills**, invoked per stage (each has an adapter-level fallback):
  `figma-feature-spec` (shipped here) · `import-figma-assets` · `figma-design-to-code` /
  `figma-swiftui` · `pfw-modern-swiftui` · `swiftui-ui-patterns` · `pfw-composable-architecture` ·
  `swiftui-view-refactor` · `design-compare` · `pfw-testing` · `swift-code-reviewer-skill`.

Missing capabilities are reported as a single up-front blocker list, not discovered one by one
halfway through the build.

## Install

```bash
git clone https://github.com/gwair1989/figma-full-cycle.git
cd figma-full-cycle
./install.sh
```

`install.sh` symlinks both skills into `~/.claude/skills` — so `git pull` updates them in place.

```bash
./install.sh --target ~/.codex/skills   # Codex
./install.sh --target .claude/skills    # this project only
./install.sh --copy                     # copy instead of symlink
./install.sh --force                    # replace an existing skill of the same name
./install.sh --uninstall                # remove what it installed
```

Already keeping these skills in your skills directory? `--force` replaces them and moves the old
copies to `.skill-backups` **next to** the skills directory — never inside it, where an agent would
pick the backup up as a second, duplicate skill.

Verify: start a new agent session and check that `figma-full-cycle` appears in the skill list.

## Use

Give the skill the link to the **parent** frame — the container holding every screen of the flow,
not a single screen:

```text
Сделай фичу по фигме целиком: https://figma.com/design/<fileKey>/App?node-id=1234-5678
```

```text
Полный цикл по фрейму <url>, режим: ui-first — тз позже
```

```text
Продолжи <FEATURE>, старт: этап 5
```

English triggers work too: *"full cycle from Figma frame"*, *"implement feature from Figma flow"*,
*"UI first, logic later"*.

### What it writes into your project

| File | Tracked | Role |
|---|---|---|
| `docs/<FEATURE>_PIPELINE.md` | yes | Manifest: stages, gates, evidence, question log, decisions |
| `docs/<FEATURE>_UI_PLAN.json` | yes | Machine-checked handoff contract from spec to implementation |
| `docs/<FEATURE>_PIPELINE.local.md` | no (gitignored) | Local runtime: absolute paths, simulator UDID |

## What's in the box

```
skills/
├── figma-full-cycle/
│   ├── SKILL.md                     # the orchestrator
│   ├── adapters/                    # claude-code.md, codex.md — capability → tool names
│   ├── references/                  # UI plan contract, Figma acquisition, strings, conventions
│   ├── scripts/                     # ui_plan.py, localization_context.py (+ tests)
│   ├── templates/                   # PIPELINE, PIPELINE.local, UI_PLAN
│   └── agents/openai.yaml           # OpenAI-style agent manifest
└── figma-feature-spec/              # stage 1 as a standalone skill
    ├── SKILL.md
    └── templates/SPEC.template.md
```

### The two scripts

Both are read-only, stdlib-only CLIs — the skill calls them so the model never has to swallow raw
data:

```bash
python3 skills/figma-full-cycle/scripts/ui_plan.py validate \
  --plan docs/FEATURE_UI_PLAN.json \
  --manifest docs/FEATURE_PIPELINE.md \
  --project-root . --phase ui
```

`ui_plan.py` validates the implementation contract — screens, components, tokens, copy, assets and
their provenance — and returns small, actionable diagnostics before a build loop starts.

```bash
python3 skills/figma-full-cycle/scripts/localization_context.py inventory --root .
```

`localization_context.py` inspects `.xcstrings` / `.strings` / `.stringsdict` with bounded output:
`inventory`, targeted `lookup`, key-level `diff`, `validate`. It never writes catalogs and never
prints them whole.

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

It runs the 32 validator tests on every Python 3 the machine has — including
`/usr/bin/python3`, the 3.9 that ships with the Xcode Command Line Tools — then lints skill
structure and shell syntax. To make that automatic before every push:

```bash
ln -sf ../../tools/pre-push .git/hooks/pre-push
```

CI only checks skill structure and relative links: things a reviewer cannot eyeball in a diff.

## License

[MIT](LICENSE) © Oleksandr Khalypa
