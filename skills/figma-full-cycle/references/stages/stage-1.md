# Stage 1 — Spec + UI Plan

**Read before starting** (skip what the session already holds): [`../ui-plan-contract.md`](../ui-plan-contract.md); [`../strings-workflow.md`](../strings-workflow.md) unless the Strings row resolved `not-applicable`. The acquisition contract was read at preflight.

## Role binding

`feature-spec` (pinned `figma-feature-spec`) over the `design-source-read` binding, per the acquisition contract:

- Load the `design-to-code-workflow` binding before the first context call.
- One metadata map for the parent/large frame → scoped `get_design_context` as the primary read for the selected children.
- Separate screenshot / variable defs / Code Connect only for evidence gaps.
- Reconcile copy from Figma against the resolved Strings contract; build one deduplicated feature copy inventory and run one batched lookup.
- Fill the compact UI Plan from the spec and the project contract. Describe layout as containers and relations, never as artboard coordinates — absolute positions from design context do not enter the plan as a layout technique.
- A static mockup is not a source of behavior — question or TBD (in `ui-first`, `deferred-to-spec`).

## Fallback

- `design-to-code-workflow` unbound → its documented fallback, without faking a declared name.
- Code Connect unavailable → project audit.
- `design-source-read` blocked → blocker.

## Gate

- Capability ledger and Figma access probe recorded.
- Figma capability / source quality / provenance recorded.
- Spec and UI Plan on disk.
- `ui_plan.py --phase ui` passes.
- Blockers answered.
- Every copy and mapping has provenance and status.
