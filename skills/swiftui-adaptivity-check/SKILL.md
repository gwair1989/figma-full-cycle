---
name: swiftui-adaptivity-check
description: 'Use when checking existing SwiftUI screens across device sizes, safe areas, appearances, text sizes, locales, orientations or keyboard states. Works without Figma, standalone or as stage 6 of figma-full-cycle. Triggers: "проверь адаптивность", "проверь экран на маленьком айфоне", "проверь вёрстку на разных устройствах". Not for Figma visual fidelity or implementing business logic.'
---

# SwiftUI Adaptivity Check

Validate existing UI against its supported device/configuration matrix. Owns the adaptivity
workflow and completion criteria used independently and by `figma-full-cycle` stage 6.

## Inputs and setup

- Required: project/screens or native captures, with supported configuration boundaries.
- Optional: selected states, device/configuration overrides, design references, output path,
  permission to fix findings, pipeline context.
- Default report: `docs/<RUN>_ADAPTIVITY.md`.

Read [validation-context.md](../_figma-full-cycle-shared/references/validation-context.md) first:
it defines modes, audit, discovery, physical checks, fix scope and reports. `<shared-root>` is the
sibling `_figma-full-cycle-shared`. Standalone use needs no manifest, UI Plan, Figma URL,
Figma credential or mock screenshot.

Read LAY-11/12/13 in the shared
[Layout contract](../_figma-full-cycle-shared/references/layout-adaptivity-contract.md). LAY-11 owns
device bounds, Preview/evidence requirements, edge-invariant tolerance and minimum manual coverage.
Reuse supplied constraints or derive them from project docs, the brief and relevant views.
Unknown support boundaries are a coverage question; one reference device cannot represent the app.

## Workflow

1. Build/label the required matrix from deployment target, screen states and resolved Layout,
   Typography, Strings and Accessibility constraints. Alongside LAY-11 devices include light/dark,
   supported content sizes, documented locales/directions and long copy, supported orientations,
   keyboard and safe-area cases. VoiceOver, Reduce Motion and increased contrast require an active
   Accessibility requirement.
2. Bring screens up directly and capture every required row. Keep geometry-bearing screens'
   smallest/largest Previews required by LAY-11; adding them needs existing fix authorization,
   otherwise report missing required Previews as a finding. Supplied captures cover only their
   documented rows. A minimal available device supplies partial evidence and never closes
   unavailable required configurations.
3. Choose evidence **per row**:
   - **Actual design/mock available:** use recorded provenance/pin and run the shared helper when
     `sips` is available. Only rows with real references enter the batch plan:

     ```bash
     python3 <shared-root>/scripts/screenshot_diff.py batch \
       --plan <artifact-root>/reports/matrix.json --project-root <project-root> \
       --out <artifact-root>/reports/matrix-result.json
     ```

     Items are `{label, render, mock, ignore_top, ignore_bottom}`. Record actual markers/JSON.
     Follow shared Figma acquisition only when fetching Figma evidence; local design captures
     need no Figma call.
   - **No design/mock, or no `sips`:** mark geometry `not-run` with its reason. Inspect **every
     row** against native bounds/project invariants. Do not fabricate a design from another render,
     stretch a reference-device capture into a mock, or emit a mechanical clean marker.
     Direct review is a complete supported validation path.
4. Apply LAY-11 manual coverage to mechanically checked rows. Its cross-aspect clipping limits
   remain binding; inspect truncation/reflow, overlap and control placement. Verify intended edge
   relations on smallest/largest targets and the system-owned root shape, including oversized
   decoration, under shared rules.
5. For pending translations use sanctioned pseudolocales/fixtures or retain pending coverage/an
   approved waiver under project policy. Do not manufacture translations. Track source-layout
   success separately from translation readiness.
6. Write the shared report with the full required matrix, including unexecuted rows, measured
   edge distances, reviewed evidence and fixes/rechecks. Authorized UI changes invalidate affected
   comparison/adaptivity/physical results; return these rows to the orchestrator in pipeline mode.
   Return report path, result and coverage gaps.

## Completion criteria

- Every required row has reviewed evidence: UI fits, no unintended letterboxing, clipping or
  overlap, and background reaches system-provided edges.
- LAY-11 edge-invariant, Preview and manual-review requirements are met; unavailable required
  configurations stay open rather than being replaced by an available device.
- Mechanical rows contain actual markers/JSON; no-reference/no-helper rows name the fallback
  and have direct review for every row.
- Translation readiness is explicit and required physical checks meet the shared contract.
- A passing result has no required row `failed`, `blocked`, `not-run` or `stale`. A skipped
  mechanical pass can coexist with a passed row after its required direct review.
