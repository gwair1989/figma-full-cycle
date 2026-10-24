---
name: figma-design-compare
description: 'Use when comparing implemented SwiftUI screens or native app screenshots against a Figma frame, reporting visual differences, or verifying requested visual fixes. Works standalone or as stage 5 of figma-full-cycle. Triggers: "compare the screen with Figma", "compare the implementation with the mockup", "check design fidelity". Not for implementing a new flow or checking adaptivity without a design reference.'
---

# Figma Design Compare

Compare an existing implementation with a pinned Figma design. Owns the comparison workflow
and completion criteria used independently and by `figma-full-cycle` stage 5.

## Inputs and setup

- Required: Figma URL with relevant node, and runnable screens or supplied native app captures.
- Supply/discover project root, screen/state mapping, capture devices and build details.
- Optional: output path, approved deviations, permission to fix findings, pipeline context.
- Default report: `docs/<RUN>_DESIGN_COMPARE.md`.

Read [validation-context.md](../_figma-full-cycle-shared/references/validation-context.md) first:
it defines modes, project audit, discovery, physical checks, fix scope and reports.
`<shared-root>` is the sibling `_figma-full-cycle-shared`. Standalone use needs no manifest/UI Plan.

Before Figma reads, load the shared
[acquisition contract](../_figma-full-cycle-shared/references/figma-mcp-acquisition.md).
Use the authenticated read capability available. Standalone use needs no separate
`FIGMA_ACCESS_TOKEN` when authenticated MCP reads supply required evidence; pipeline-specific
credential checks belong to the caller. Missing design access blocks comparison.

Read LAY-07 and comparison rules in the shared
[Layout contract](../_figma-full-cycle-shared/references/layout-adaptivity-contract.md), plus
COL-06/07 in the [Colors contract](../_figma-full-cycle-shared/references/colors-contract.md).

## Workflow

1. Establish the Figma pin (file, node, version/hash) in the report or verify the caller's pin
   before reusing evidence. Changed design invalidates dependent comparisons and is reported.
   Apply shared acquisition/cache rules; keep raw responses out of the report.
2. Identify selected screens/states. Obtain the full screen/frame screenshot with its parent
   context; isolated icon/asset exports are not style references. Get exact typography/color
   values from design context and record deviations required by project conventions.
3. Capture each selected screen at reference size and at least one non-reference size, using
   Preview, simulator or requested native device capture. Supplied evidence lacking either size
   leaves coverage open. Runtime navigation is outside this comparison.
4. Run geometry over **every pair** when `sips` and the shared helper are available:

   ```bash
   python3 <shared-root>/scripts/screenshot_diff.py compare \
     --render <native-render.png> --mock <pinned-frame.png> \
     --label "<screen>/<state>/<device>" \
     --ignore-top <status-bar> --ignore-bottom <home-indicator> \
     --out <artifact-root>/reports/diff-<pair>.json
   ```

   The helper normalizes the mock. Different aspect ratios leave the structural grid ungated;
   this diagnostic cannot prove adaptation. Without `sips`, mark geometry `not-run` and review
   every pair visually under the same rules.
5. Visually compare every `FAIL`, one content-dense `PASS` pair per screen, and **every
   non-reference pair regardless of mechanical result**. Use an available specialized reviewer
   or inspect images directly; never route review back into this skill. Check typeface, icons,
   copy and subtle colors as well as geometry: the script cannot verify them.
6. Apply shared inset tolerance, relational geometry and system-owned root-shape rules. Confirm
   intended equal-edge relations on the non-reference size with the shared tolerance. Explain
   contract-required deviations. For authorized fixes, fix causes, recapture and recompare.
   Pipeline calls return affected assets/screens for the orchestrator's stage 2/3 loop-backs.
7. Write the shared report. Pair rows also identify the Figma screen node/version and contain a
   nonempty **Looked at by eye** field naming reviewed pairs and method. Return report path,
   result, unresolved findings and coverage gaps.

## Completion criteria

- Report on disk with pin, explained deviations and reference/non-reference coverage per screen.
- Every mechanical comparison records actual `SCREENSHOT_DIFF_CLEAN` / `SCREENSHOT_DIFF_DIRTY`
  markers and JSON paths, or an explicit fallback reason.
- Every pair selected for visual review above was inspected and recorded.
- A passing result has no unresolved visual defect; authorized fixes were recaptured/recompared.
  Required physical rows meet the shared evidence contract.
- Audit-only use reports remaining defects as `failed`; it does not silently fix or claim a pass.
