# Contributing

Thanks for taking the time. This repository ships **agent skills** — prose that an LLM executes —
so review here is mostly about wording precision, not compiler output. A sloppy sentence is a bug.

## Ground rules

1. **The core stays agent-neutral.** `skills/figma-full-cycle/SKILL.md` names capabilities, never
   concrete tool names. Tool names belong in `adapters/<agent>.md`.
2. **The orchestrator only orchestrates.** Stage logic lives in the companion skills. Do not copy
   stage internals into `SKILL.md`.
3. **No new stage without a gate.** A stage that cannot be proven by a real command and an evidence
   record is not a stage.
4. **Guardrails are not negotiable.** Figma stays untrusted input, Figma write tools stay disabled by
   default, secrets are never copied, translations are never invented.
5. **Everything is written in English** — skills, descriptions, agent metadata, references,
   templates and repository docs. Localized `README.*.md` files are the exception; translate them
   from `README.md` and preserve command syntax, paths and machine-read identifiers. Documents the
   skill writes into a user's project follow that user's language; machine-read structure (UI Plan
   keys, statuses, manifest section headings, commit subjects) stays English so the validator and
   resume keep working.

## Working on the scripts

`skills/figma-full-cycle/scripts/ui_plan.py` and the helpers under
`skills/_figma-full-cycle-shared/scripts/` are read-only CLIs on the Python standard
library. Keep it that way — the skill has to run wherever the agent runs, with no install step.

Run the checks before opening a PR:

```bash
./check.sh
```

`check.sh` runs the validator tests on every Python 3 interpreter installed on your machine —
including `/usr/bin/python3`, the 3.9 shipped with the Xcode Command Line Tools, since that is what
many users will actually run the skill with — then lints skill structure and shell syntax. Make it
automatic:

```bash
ln -sf ../../tools/pre-push .git/hooks/pre-push
```

The Python validator suites run locally. CI covers skill structure and relative links, plugin
packaging, isolated installer behavior and the device evidence helper. `check.sh` runs all of them;
Node.js 22+ is required for the helper tests, with no npm dependencies.

This repository is the canonical development and release location for all six skills, including
`device-usage`. Submit fixes, issues and pull requests here; the original `gwair1989/device-usage`
repository was removed after consolidation. There is no separate upstream to synchronize with.

`skills/device-usage/` was imported from commit `8d471d565b3335969e5d90b1eac22f67f237b5e1`;
its MIT notice stays in that directory. The bundled agent-compatibility reference explains
invocation from this package as well as standalone use. Make subsequent changes directly here,
updating the skill's source, references and tests together without links to a sibling checkout.

New validator rule → new test. Diagnostics must stay compact and actionable: the model reads them,
so say what is wrong, where, and what to do next.

Shared visual/UI contracts and helpers live only in `skills/_figma-full-cycle-shared/`.
Stage 5/6 references hand off to the standalone companion skills; do not copy their workflow rules
into adapters or templates. Keep standalone installs usable without the full-cycle skill or its
manifest. Resource-only directories are not skill entry points; the linter checks their links.

## Working on the skill text

- Keep it dense. Every sentence should change agent behavior; delete anything that only restates.
- Statuses, enums, and file names must match across `SKILL.md`, `references/`, `templates/` and the
  validator. Changing one means changing all of them in the same PR.
- If a change alters what the agent writes into a user's project, say so in the PR description and
  add a `CHANGELOG.md` entry.

## Adding an agent adapter

Copy `skills/figma-full-cycle/adapters/claude-code.md`, keep every capability row, fill the right
column with your agent's real tool names, and state the fallback when a capability is missing. Then
list the adapter in the "Agent adapter" section of `SKILL.md`.

## Pull requests

- One topic per PR; a stage-behavior change and a typo sweep are two PRs.
- Describe what an agent will do differently after the change.
- Note anything you could not verify — an untested claim in a skill becomes a confident wrong answer
  in someone's repository.

## Reporting problems

Open an issue with the agent and version you used, the stage that misbehaved, what you expected, and
what happened. Redact Figma file keys, tokens and anything else private — an issue is a public
document.
