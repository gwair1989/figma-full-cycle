# {{FEATURE_NAME}} — Feature Spec

Status: **DRAFT (stage 1 — spec before implementation)**
Design source: Figma file `{{FILE_KEY}}` — frame `{{ROOT_NAME}}` (`{{ROOT_NODE_ID}}`), {{FRAME_COUNT}} frames = {{SCREEN_COUNT}} unique screens.
Entry point: {{ENTRY_POINT}}.
Exit point: {{EXIT_POINT}}.

Stage numbers follow `figma-full-cycle`. Standalone use of `figma-feature-spec` produces only this spec.

## Legend

- **View** — the SwiftUI View name. Filled in at stage 3 (UI implementation). For now, the suggested name in parentheses.
- **Logic** — a draft. `Data/API` marked `TBD` is detailed at stage 7 (business logic and services).
- **Assets** — Figma node-ids for import via the `import-figma-assets` skill (stage 2).
- Copy typos present in the design are marked `⚠️ typo`; the code uses the corrected strings through the centralized copy mechanism.

## Architecture note

<!-- Required: the architecture selected by project documentation or the user, its source
(path#section or recorded user decision), and the relevant state, navigation and dependency
boundaries. Resolve missing or conflicting documentation with the user before completing the spec;
do not choose a pattern from code or installed skills. State / Actions below are conceptual,
not mandatory framework types. -->
{{ARCH_NOTE}}

---

## Screens

<!-- Repeat this block for every unique screen. -->

### {{N}}. {{SCREEN_NAME}}

- **Figma:** [{{NODE_ID}}]({{FIGMA_URL}}){{EXTRA_STATE_LINKS}}
- **View:** _TBD_ (suggested `{{SUGGESTED_VIEW}}`)
- **Description:** {{DESCRIPTION}}
- **States:** {{STATES_OR_NONE}}
- **Assets (import-figma-assets):**
    - `{{ASSET_NODE_ID}}` — {{ASSET_DESC}} — {{raster|vector}} — suggested name `{{ASSET_NAME}}`
- **Logic (draft):**
    - **State:** {{STATE_DRAFT}}
    - **Actions:** {{ACTIONS_DRAFT}}
    - **Navigation:** {{NAV_DRAFT}}
    - **Data/API:** TBD
- **Implementation tasks (stage 3):**
    - [ ] {{LAYOUT_TASK}}

---

## Navigation Map

```mermaid
flowchart TD
{{NAV_MAP}}
```

<!-- Mark edges inferred by guesswork (not explicit in the design) with `?` in the label. -->

---

## Open questions / assumptions (to confirm)

<!-- Everything the design cannot answer: required fields, data source (API vs static),
field dependencies, what ships as a stub, back behavior, how the flow is exited. -->

1. {{OPEN_QUESTION}}

## Following stages

- **Stage 1 (now):** complete this spec and resolve blocking questions; the full cycle also creates and validates the UI Plan.
- **Stage 2:** import and validate assets from the node-id inventory.
- **Stage 3:** implement the SwiftUI screens and architecture skeleton; fill in the real `View` names.
- **Stage 4 (conditional):** refactor the UI when complexity, view size or lint findings require it.
- **Stage 5:** compare the implemented screens with the pinned Figma design, including a non-reference device size.
- **Stage 6:** validate adaptivity across the required devices, appearances, content sizes, locales and keyboard states.
- **Stage 7:** implement business logic and runtime navigation under the resolved architecture; verify with tests.
- **Stage 8:** complete final review, repeat affected checks and commit the clean checkpoint.

In `ui-first` mode, stages 7–8 wait for requirements after stage 6.
