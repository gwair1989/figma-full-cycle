# Stage 8 — Final

**Read before starting** (skip what the session already holds): the LAY-01…LAY-04, LAY-08…LAY-10, LAY-12, LAY-13 and COL-01…COL-05 rules being re-detected — [`../layout-adaptivity-contract.md`](../layout-adaptivity-contract.md), [`../colors-contract.md`](../colors-contract.md).

## Role binding

`code-review`; fix the findings.

Then:

- Re-run the LAY-01…LAY-04, LAY-08…LAY-10, LAY-12, LAY-13 and COL-01…COL-05 detections — or the project's color guard — over the changed files, with the same invocation stage 3 recorded:

  ```bash
  python3 <skill-root>/scripts/ui_guard.py check --project-root . --changed-since <BASE_SHA> --reference-canvas <W>x<H> --asset-catalog <path/to/Assets.xcassets>
  ```

  A waiver added since stage 3 is reviewed here, not accepted because it is already in the file.
- If UI or copy changed → targeted stages 5/6 and a repeated Strings key-level gate for the changed `copy_id` only.
- If required physical-device routes were affected → repeat those checks through `physical-device-control`; no required row may remain failed, blocked, not-run or stale at finalization.

## Fallback

No stack-specific reviewer → a generic review command, else the agent's built-in review path. **The stage is never skipped.**

## Gate

- Review clean.
- No raw user-facing literals outside the allowed mechanism and no unexpected Strings keys.
- Layout and color detections clean or waived.
- Final clean checkpoint committed.
