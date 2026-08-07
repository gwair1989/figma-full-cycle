# Stage 5 — Design comparison

**Read before starting** (skip what the session already holds): the LAY-07 snap window and §3 of [`../layout-adaptivity-contract.md`](../layout-adaptivity-contract.md); COL-06 of [`../colors-contract.md`](../colors-contract.md). Both are normally still in session from stage 3.

## Role binding

Re-check the Figma pin, then `visual-comparison` per screen (`#Preview` or a simulator screenshot; one explorer subagent per screen).

- The style reference is the **full screenshot of the parent frame**: an isolated node export bakes in screen backgrounds and is only good for slicing assets.
- Verify Typography/Colors and other numbers from design context, not by pixel approximation.
- Mark intentional deviations coming from the resolved contract explicitly.
- Compare every screen on at least one **non-reference** size as well: at the reference size a fixed canvas matches pixel-for-pixel and hides the breakage.
- An inset divergence inside the LAY-07 system-value snap window (−2…+4pt) is a match, not a defect.

## Mechanical pass first

Before any screen goes to a subagent or into the model's own eyes, run the geometry check:

```bash
python3 <skill-root>/scripts/screenshot_diff.py compare \
  --render docs/.cache/<FEATURE>/screenshots/<screen>@<device>.png \
  --mock docs/.cache/<FEATURE>/figma/<nodeId>.screenshot.png \
  --label "<screen>/<device>" --ignore-top <status bar> --ignore-bottom <home indicator> \
  --out docs/.cache/<FEATURE>/reports/diff-<screen>-<device>.json
```

It normalizes the mock to the render's size, so a non-reference device is a normal comparison rather than an error, and it answers letterbox / pillarbox / background-to-the-edges / bottom-clipping in about 0.3s.

**It is not the gate.** It sees geometry, not design: a wrong typeface, a mirrored icon, wrong copy or a shade under the threshold all pass, and it prints that list with every run. Eyes go on every `FAIL`, and on **one `PASS` per screen** — a screen whose every row passed mechanically has still never been looked at.

## Fallback

- `visual-comparison` unbound → manual comparison against the parent-frame screenshot under the same rules and evidence.
- No `sips` (non-macOS host) → the mechanical pass is skipped and every pair is compared by eye; record that in the gate evidence, because the gate just got wider, not narrower.
- No `FIGMA_ACCESS_TOKEN` → blocker before the stage.

## Gate

- Report on disk.
- ❌ items fixed and re-compared.
- Contract deviations explained.
- A non-reference size covered per screen.
- The mechanical pass ran, its `SCREENSHOT_DIFF_CLEAN` / `SCREENSHOT_DIFF_DIRTY` marker and report path recorded, and every `FAIL` plus one `PASS` per screen reviewed by eye.

`#Preview` ≠ the flow — runtime navigation belongs to stage 7.
