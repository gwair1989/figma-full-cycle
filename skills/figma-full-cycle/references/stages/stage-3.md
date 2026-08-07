# Stage 3 — UI implementation + architecture skeleton

**Read before starting** (skip what the session already holds): [`../layout-adaptivity-contract.md`](../layout-adaptivity-contract.md) and [`../colors-contract.md`](../colors-contract.md) in full — this is the stage that enforces LAY-01…LAY-10 and COL-01…COL-09.

## Role binding

Consume only the validated UI Plan.

- A bound `design-to-code-workflow` is a mandatory workflow prerequisite before `get_design_context`; a bound `platform-design-translator` complements it, never replaces it.
- Target: `clientLanguages=swift`, `clientFrameworks=swiftui`. Declare a name in `skillNames` only when that exact registered name was discovered **and** loaded (resource prefix per the acquisition contract).
- Then `platform-ui-idiom` + `app-architecture` (skeleton `State`/`Action`, the view binds to the Store).
- MCP and skill output is an intermediate structure; the UI Plan, spec and project contract define scope and behavior and forbid inferred navigation, data or persistence.

Per area:

- **Strings** — implement in one batch and run one documented extraction/generation/project-build cycle plus a key-level `diff`/`validate`.
- **Typography** — only through the project's resolved contract.
- **Accessibility** — only on an explicit requirement.
- **Colors** — the resolved Colors contract and rules COL-01…COL-09: the view references a semantic token, never a palette entry or an inline literal in any form, and a value with no token is a question, not an improvisation.
- **Layout** — the resolved Layout contract and rules LAY-01…LAY-10: native flexible layout, never a fixed reference canvas with a global `scaleEffect`, never absolute `position`/static `offset` as layout, however the design-to-code output arrives.

## Fallback

- `design-to-code-workflow` unbound → do not fake `skillNames`, use its documented fallback.
- `platform-design-translator` unbound → the generic binding plus the project's UI skills and precedent.

## Gate

- UI Plan hash and evidence current.
- Component and token targets verified in the project.
- Expected Strings keys verified.
- Build succeeds.
- Every screen and state is `done`.
- No resolved UI convention bypassed.
- LAY-01…LAY-10 and COL-01…COL-05 detections run over the feature's changed files — or the project's own color guard with its documented invocation — and come back clean or waived in the manifest:

  ```bash
  python3 <skill-root>/scripts/ui_guard.py check --project-root . --changed-since <BASE_SHA> --reference-canvas <W>x<H> --asset-catalog <path/to/Assets.xcassets>
  ```

  The mechanical half only. Record the command, its `UI_GUARD_CLEAN` / `UI_GUARD_DIRTY` marker and the coverage note as gate evidence, and check the rules the run lists as `reviewer` by hand — a clean run is exactly as wide as that note.
