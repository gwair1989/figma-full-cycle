---
name: figma-feature-spec
description: 'Use when given a Figma frame link/URL for a whole feature or flow and a written spec is needed before any coding — turning the frame''s child screens into a pre-implementation spec document. Triggers: "write a spec from Figma", "break down the frame into screens", "figma flow to spec", "feature spec from frame", pre-implementation design doc from a Figma parent frame.'
---

# Figma Feature Spec

## Overview

From a link to the **parent frame of a feature in Figma**, generates a **written spec document**
(stage 1, before any implementation): screen list, navigation map, per-screen asset inventory and a
draft checklist of implementation tasks.

**Three artifacts in one md:** (1) the screen spec following the template, (2) the asset inventory
(node-ids for `import-figma-assets`), (3) the implementation task checklist for stage 3.

**Spec only. Do NOT write code or UI (stage 3), and do NOT import assets (stage 2).** Product decisions
(whether a field is required, API vs static data, final navigation) are **never invented** — they go
to "Open questions / assumptions".

Template: `templates/SPEC.template.md` (canonical structure).

## Prerequisites

- Figma MCP connected and authenticated. Before any Figma tool call, load the Figma workflow skill your agent's catalog actually registers — take the name from the live listing, not from memory; inside `figma-full-cycle`, reuse the `design-to-code-workflow` binding from the capability ledger. If nothing is registered, proceed without it rather than declaring a name that is not loaded.
- A link to the **parent** frame containing every screen of the feature — not to a single screen.

## Inputs

- **Required:** a Figma URL shaped `https://figma.com/design/:fileKey/:name?node-id=1-2` → extract
  `fileKey` and `node-id`.
- Optional: feature name (otherwise taken from the frame name), output path (default
  `docs/<FEATURE>_SPEC.md`), an explicit architecture decision from the user for this feature.

## Resolve the architecture

Before drafting the Architecture note, reuse the resolved Project architecture contract when running inside `figma-full-cycle`. For standalone use, read applicable project instructions, `README*`, architecture documents / ADRs and module documentation. If no explicit user decision is already available and those documents are missing, ambiguous or contradictory, ask the user which architecture to follow before completing the spec. Do not infer the choice from source code, dependencies, Figma or installed skills.

Record the selected architecture and its source (`path#section` or user decision) in the Architecture note, with the state ownership, navigation and dependency boundaries needed for this feature. Code may confirm implementation details within that choice. There is no default architecture or mandatory reducer / Store structure; copy and asset conventions still follow the project.

## Workflow

1. **Parse the URL** → `fileKey` + `nodeId`.
2. **`get_metadata`** on the parent frame → inventory of child frames: `node-id`, name, `w×h`. This
   is the map of screens and states.
3. **Group into unique screens.** Several frames are often states of one screen (deduplicate by name
   or visual: empty/typing/filled/selected). Take one `get_screenshot` per unique screen; call
   `get_design_context` only where copy, colors, dimensions or structure are actually needed.
4. **Fill the template block per screen:**
   - Description derived from the visual (what the screen is, key elements).
   - **Asset inventory:** node-ids of icons, photos and illustrations that stage 2 will feed to
     `import-figma-assets`; classify raster vs vector; propose an asset name. Mark a complex masked
     illustration as "flatten export".
   - Draft logic: State / Actions / Navigation / Data-API=TBD. State and Actions describe data and interactions conceptually; they do not prescribe framework types or an architecture.
   - `View: _TBD_ (suggested <Name>View)`.
   - Implementation task checklist (what to build, which states, which assets).
5. **Navigation map (mermaid)** — from frame order, names and CTA buttons. Mark guessed edges with `?`.
6. **Copy typos** — find them (e.g. "Add animail", "Galery"), mark `⚠️ typo`, and note "the code uses
   the corrected string through the centralized copy mechanism".
7. **Open questions / assumptions** — collect everything the design cannot answer: required fields,
   source of reference data (API vs static), field dependencies, what ships as a stub, back
   behavior, exit point.
8. **Write** `docs/<FEATURE>_SPEC.md` from `templates/SPEC.template.md` (Write). Return the path plus
   a short summary (screen count, asset count, open question count).

## Quick Reference — Figma MCP

| Need | Tool |
|------|------|
| List of child frames | `get_metadata(fileKey, nodeId)` |
| Screen image | `get_screenshot(fileKey, nodeId)` |
| Copy / colors / dimensions / assets | `get_design_context(fileKey, nodeId)` |
| Variables and tokens | `get_variable_defs(fileKey, nodeId)` |

At stage 1 assets are **inventoried only** (node-id + classification). Downloading and
`download_assets` belong to stage 2.

## Guardrails

- **Never invent product decisions.** Anything the design does not state goes to "Open questions" as
  a `TBD`, not into the spec as a fact.
- **Spec only:** no code, no asset import, no project edits beyond the single md file.
- **Output language follows the user's language** — the language of the request, unless the user asks
  for another. Structural markers stay as the template defines them so downstream stages can parse
  the document.
- **Copy:** the spec carries corrected strings, design typos are flagged, and typos never leak into
  the "strings for code" section.
- Follow project rules (AGENTS.md / CLAUDE.md): never touch the baseline or sibling worktrees.

## Common Mistakes

- A link to one screen instead of the parent frame → `get_metadata` returns almost nothing; ask for
  the link to the flow's container frame.
- Treating every frame as a separate screen → collapse states of the same screen instead.
- Reading the asset inventory as "download now" → it is only node-ids for stage 2.
- An empty navigation map → derive at least the linear chain from frame order and mark uncertain
  edges with `?`.
- Calling `get_design_context` on every frame in sequence → expensive; call it where details are
  genuinely needed.
