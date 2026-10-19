# Stage 7 — Business logic

**Read before starting:** the resolved Project architecture contract from the manifest. Reuse the state ownership and interaction interfaces established at stage 3; the UI Plan is already in session.

In `ui-first`, this stage waits for the requirements.

When physical iPhone routes are requested, run them through `physical-device-control` per [`../device-validation.md`](../device-validation.md), with observed route results and evidence. This runtime walkthrough complements the automated tests below.

## Role binding

`app-architecture` (business rules, async work and dependencies implemented through the stage 3 interfaces under the resolved architecture) + `test-authoring` (no test target in the project → create it here).

Plus:

- Runtime navigation: happy / error / cancel / back.
- Loading / empty / error / offline states.
- Business-rule tests and async-work / cancellation tests where applicable, using the resolved architecture's testing approach.
- API = TBD → stub with a log entry.

## Fallback

No matching architecture skill → implement directly under the documented or user-confirmed architecture contract. An absent or conflicting contract requires a user answer; source-code precedent alone does not resolve it.

## Gate

- `ui_plan.py --phase production` passes.
- Logic, navigation and dependencies follow the resolved architecture contract.
- All tests pass.
- Build succeeds.
- Required physical-device routes passed with reviewed evidence, or remain explicitly blocked; simulator success does not close them.
- TBDs in the log with a merge-blocking flag.
