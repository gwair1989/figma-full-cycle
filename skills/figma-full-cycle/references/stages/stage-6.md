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

The four LAY-11 questions — layout fits, no unintended letterboxing, no clipped content, background reaching the edges — are exactly what the script answers, which is why it exists. What it cannot answer stays with the reviewer: text that is truncated rather than clipped, a locale that reflows badly, a control that moved somewhere legal but wrong. Eyes go on every `FAIL`, and on one `PASS` per screen.

## Fallback

- No device → the minimal available one.
- No `sips` → no mechanical pass; every row is confirmed by eye and that is recorded in the evidence.

## Gate

- Every row required by the resolved contract shows no clipping or overlap.
- Per required device the screenshot evidence explicitly confirms: the layout fits the screen, no unintended letterboxing, no clipped content, background reaching the edges.
- The batch run's marker and report path are recorded; every `FAIL` and one `PASS` per screen were reviewed by eye.
- Translation readiness tracked separately from the source gate.
- Evidence stored.
