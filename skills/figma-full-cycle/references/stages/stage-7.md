# Stage 7 — Reducer logic

**Read before starting:** nothing new. `State`/`Action` come from the stage 3 skeleton; the UI Plan is already in session.

In `ui-first`, this stage waits for the requirements.

## Role binding

`app-architecture` (reducer bodies, effects, dependencies; `State`/`Action` from stage 3) + `test-authoring` (no test target in the project → create it here).

Plus:

- Runtime navigation: happy / error / cancel / back.
- Loading / empty / error / offline states.
- Effect and cancellation tests.
- API = TBD → stub with a log entry.

## Fallback

No architecture skill for the project's stack → its existing patterns, read from code and docs.

## Gate

- `ui_plan.py --phase production` passes.
- All tests pass.
- Build succeeds.
- TBDs in the log with a merge-blocking flag.
