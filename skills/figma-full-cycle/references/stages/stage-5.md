# Stage 5 — Design comparison

## Role binding

`visual-comparison` is bundled [figma-design-compare](../../../figma-design-compare/SKILL.md),
resolved by its exact registered name including any plugin namespace. The companion owns the
workflow, shared-rule references, fallbacks and completion criteria.

## Pipeline handoff

- Supply current project contracts, spec/UI Plan screen-state mapping, Figma pin, artifact root,
  Design comparison rows, capture/build bindings and required Physical device checks.
- The pipeline-specific `FIGMA_ACCESS_TOKEN` must be present; absence blocks this stage.
  Never print its value. The companion verifies the pin before comparison.
- Request in-scope fixes under existing feature authorization. Only the orchestrator writes the
  manifest, handles asset/structural loop-backs to stages 2/3, invalidates dependent rows and commits.
- Import the report, actual mechanical markers/fallbacks and reviewed pair coverage, including the
  nonempty Looked at by eye column. A changed pin or implementation makes dependent checks stale.

## Gate

The companion's completion criteria must pass for every required screen/row. Record its report
and gate evidence in the manifest; unresolved defects or coverage gaps keep the stage open.
Missing companion is a capability blocker, not permission to skip comparison.
