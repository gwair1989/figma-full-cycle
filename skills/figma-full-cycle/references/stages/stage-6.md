# Stage 6 — Adaptivity

**Read before starting** (skip what the session already holds): LAY-11 of [`../layout-adaptivity-contract.md`](../layout-adaptivity-contract.md).

## Role binding

Build the matrix from the deployment target plus the spec, Strings, Layout and Accessibility contracts, per LAY-11:

- The **smallest supported device** and the largest.
- Devices **with and without a home indicator** — a different bottom safe area is a distinct bug class.
- Light/dark.
- The content sizes supported by the Typography contract.
- Documented locales and directions, and long copy.
- Orientations if supported.
- Keyboard and safe area.

Rules:

- Check pending translations only with a sanctioned pseudolocale or fixtures, or leave a pending translation gate or waiver per project policy — never generate substitute translations.
- Add AX/VoiceOver/Reduce Motion/increased contrast only under an active Accessibility contract.
- Bring the screen up directly. A screen with geometry keeps at least two `#Preview`s — smallest and largest supported device — because the default preview is the reference device and proves nothing.

## Running the matrix

The matrix is where looking costs the most — one image per row, and the row count is a product of five axes. Shoot every row, then check the whole matrix in one batch:

```bash
python3 <skill-root>/scripts/screenshot_diff.py batch \
  --plan docs/.cache/<FEATURE>/reports/matrix.json --project-root . \
  --out docs/.cache/<FEATURE>/reports/matrix-result.json
```

`matrix.json` is a list of `{label, render, mock, ignore_top, ignore_bottom}` — one entry per matrix row, the label being the row as it appears in the manifest. A 30-row matrix runs in about ten seconds and returns one `PASS`/`FAIL` line per row.

Of the four LAY-11 questions the script gates on three — unintended letterboxing, pillarboxing, background reaching the edges. Those survive a change of aspect ratio.

**Clipping does not, and this matters most on the row where it matters most.** The mock is stretched to the render's size, while a native layout adapts by holding its metrics in points, so on a different device class a correctly adapted screen also differs in the bottom band. The script reports that difference and refuses to gate on it, saying so in the output (`not gated: mock 2.17 vs render 1.78 aspect`). On the smallest supported device — a different aspect from the mock nearly every time — **whether content is clipped is a reviewer question, and that row is looked at by eye regardless of its verdict.**

Also reviewer work, on every row: text truncated rather than clipped, a locale that reflows badly, a control that moved somewhere legal but wrong. Confirm the UI Plan's edge invariants as relations: when left/right/bottom insets are intended to be equal, record their measured values (≤1pt divergence) on the smallest and largest device. Confirm that the root has no app-added device-frame mask; rectangular devices keep their system-provided corners. Eyes go on every `FAIL`, on one `PASS` per screen, and on the smallest-device row.

## Fallback

- No device → the minimal available one.
- No `sips` → no mechanical pass; every row is confirmed by eye and that is recorded in the evidence.

## Gate

- Every row required by the resolved contract shows no clipping or overlap.
- Per required device the screenshot evidence explicitly confirms: the layout fits the screen, no unintended letterboxing, no clipped content, background reaching the edges.
- Intended equal-edge insets are measured or explicitly verified on the smallest and largest device; the root presentation shape is system-owned.
- The batch run's marker and report path are recorded; every `FAIL`, one `PASS` per screen, and the smallest-device row for each screen were reviewed by eye.
- Translation readiness tracked separately from the source gate.
- Evidence stored.
