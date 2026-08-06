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
5. **Skill instructions are written in Russian.** Repository-level docs (README, this file, issue
   templates, changelog) are in English, with `README.ru.md` mirroring the main README.

## Working on the scripts

`scripts/ui_plan.py` and `scripts/localization_context.py` are read-only CLIs on the Python standard
library. Keep it that way — the skill has to run wherever the agent runs, with no install step.

Run the tests before opening a PR:

```bash
python3 skills/figma-full-cycle/scripts/tests/test_ui_plan.py
```

New validator rule → new test. Diagnostics must stay compact and actionable: the model reads them,
so say what is wrong, where, and what to do next.

## Working on the skill text

- Keep it dense. Every sentence should change agent behavior; delete anything that only restates.
- Statuses, enums, and file names must match across `SKILL.md`, `references/`, `templates/` and the
  validator. Changing one means changing all of them in the same PR.
- If a change alters what the agent writes into a user's project, say so in the PR description and
  add a `CHANGELOG.md` entry.

## Adding an agent adapter

Copy `skills/figma-full-cycle/adapters/claude-code.md`, keep every capability row, fill the right
column with your agent's real tool names, and state the fallback when a capability is missing. Then
list the adapter in the "Адаптер агента" section of `SKILL.md`.

## Pull requests

- One topic per PR; a stage-behavior change and a typo sweep are two PRs.
- Describe what an agent will do differently after the change.
- Note anything you could not verify — an untested claim in a skill becomes a confident wrong answer
  in someone's repository.

## Reporting problems

Open an issue with the agent and version you used, the stage that misbehaved, what you expected, and
what happened. Redact Figma file keys, tokens and anything else private — an issue is a public
document.
