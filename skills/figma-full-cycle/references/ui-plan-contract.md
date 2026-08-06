# UI Plan contract (schema 1)

Read this only while creating, repairing, or validating `docs/<FEATURE>_UI_PLAN.json`.
Start from `../templates/UI_PLAN.template.json`; do not invent extra behavior from static Figma layers.

## Required structure

- Non-empty arrays: `screens`, each screen's `figma_nodes`, `layout`, `states`, and `sources`.
- Arrays that may be empty: `tokens`, `copy`, `assets`, `interactions`, and `unknowns`.
- Identifiers use lowercase `[a-z0-9][a-z0-9._-]*`. Figma node IDs use `123:456` (a hyphen separator is also accepted).
- `layout` has exactly one `parent: null`; every other parent names a layout item; the hierarchy is acyclic.
- Each `figma_nodes[].state` names a declared state. A state with `source: figma` must be backed by at least one Figma node mapping.
- A `sources[]` item with `kind: figma` uses a node ID declared by that screen, not raw Figma JSON.

## Allowed values

| Field | Values | Gate rule |
|-------|--------|-----------|
| `view.status` | `existing`, `new`, `tbd` | `tbd` blocks UI implementation. `existing` is checked against project source; `new` is checked in production phase. |
| `component.kind` | `system`, `project`, `new` | `project` requires `source_ref.path` and `source_ref.symbol`; both are checked with `--project-root`. |
| `tokens[].kind` | `system`, `project` | `project` requires a checked `source_ref`. |
| copy/asset/state `status` | `resolved`, `tbd` | Copy and asset `tbd` block stage 3; state `tbd` blocks production. |
| state `source` | `figma`, `spec`, `user`, `project`, `tbd` | `figma` requires a matching node/state mapping; `resolved` cannot use `source: tbd`. |
| interaction `source` | `spec`, `user`, `figma-prototype`, `tbd` | Plain `figma` is invalid because static layers are not behavior evidence. |
| interaction `status` | `resolved`, `tbd`, `waived` | Merge-blocking `tbd` fails production; `resolved` cannot use `source: tbd`. |
| unknown `status` | `open`, `tbd`, `resolved`, `waived` | Merge-blocking `open`/`tbd` fails production. |
| source `kind` | `figma`, `project-doc`, `code`, `spec`, `user` | `ref` must identify the exact evidence. |

Any `waived` interaction or unknown requires:

```json
"waiver": {
  "reason": "Why proceeding is safe",
  "evidence": "owner/issue/decision and expiry when applicable"
}
```

## Interaction targets

`interactions[].to` is exactly one of:

- a state ID on the same screen, for example `loading`;
- another screen ID in this UI Plan, for example `receipt`;
- an explicit boundary `external:<stable-id>`, for example `external:safari-checkout`.

Do not use an undeclared free-form target such as `success`.

## Manifest and project checks

Run with both `--manifest` and `--project-root` in the real pipeline. The declared
`project_contract.manifest` must resolve inside the project root to the passed
manifest. Both manifest sections are required, even when their tables are empty.
Copy IDs are read
from `## Feature copy inventory`; asset IDs are read from `## Sub-checklist: assets
(stage 2)`, with the pre-translation heading `## Под-чеклист: ассеты` still accepted
for manifests already in flight. Cross-checking is bidirectional: neither the UI Plan
nor those feature manifest tables may silently omit the other's IDs.

For a project component/token or an existing View, `source_ref.path`/`view.path`
must stay inside `--project-root`, the file must exist, and the exact symbol must
occur in that file. In `--phase production`, the target file/symbol for a `new`
View must exist as well.

## Phase semantics and evidence

- `--phase ui`: unresolved domain behavior may remain as explicit `tbd`/`open`; structural, copy, asset, Figma, and project mappings must validate.
- `--phase production`: every merge-blocking interaction/unknown is `resolved` or has an evidenced `waived` status; the implemented target View is present.
- `--allow-placeholders`: accepted only for the bundled template path, never for a copied template or feature gate.

```sh
python3 <skill-root>/scripts/ui_plan.py validate \
  --plan docs/<FEATURE>_UI_PLAN.json \
  --manifest docs/<FEATURE>_PIPELINE.md \
  --project-root . \
  --phase ui
```

Success prints `schema` and the exact file `sha256`; copy those values into the
manifest's `UI Plan evidence` row. Errors include a JSON path, actual value,
expected constraint, and repair hint.
