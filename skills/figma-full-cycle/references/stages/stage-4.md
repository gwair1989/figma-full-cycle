# Stage 4 — UI refactor

**Conditional stage.** It runs only on findings: complexity, view size, lint. No findings → no stage.

**Read before starting:** nothing new. The Layout and Colors contracts from stage 3 still apply to whatever the refactor rewrites.

## Role binding

`view-refactor`.

## Fallback

Unbound → skip the stage and record why.

## Gate

- Build succeeds.
- Comparison and adaptivity rows for affected screens → `stale`.
