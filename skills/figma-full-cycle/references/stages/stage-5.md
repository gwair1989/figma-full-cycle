# Stage 5 — Design comparison

**Read before starting** (skip what the session already holds): the LAY-07 snap window and §3 of [`../layout-adaptivity-contract.md`](../layout-adaptivity-contract.md); COL-06 of [`../colors-contract.md`](../colors-contract.md). Both are normally still in session from stage 3.

Re-check the Figma pin before anything else. Version changed → dependent visual gates go `stale` and the user is told.

## Two passes, in this order

Comparing costs an image in context per pair, and every screen has at least two pairs (reference and non-reference size). So the stage filters first and looks second.

**1. `screenshot-geometry` over every pair.** Pinned to [`../../scripts/screenshot_diff.py`](../../scripts/screenshot_diff.py):

```bash
python3 <skill-root>/scripts/screenshot_diff.py compare \
  --render docs/.cache/<FEATURE>/screenshots/<screen>@<device>.png \
  --mock docs/.cache/<FEATURE>/figma/<nodeId>.screenshot.png \
  --label "<screen>/<device>" --ignore-top <status bar> --ignore-bottom <home indicator> \
  --out docs/.cache/<FEATURE>/reports/diff-<screen>-<device>.json
```

It normalizes the mock to the render's size, so a non-reference device is a normal comparison rather than an error, and it answers letterbox / pillarbox / background-to-the-edges in about 0.3s per pair. No image enters context here.

On a **non-reference size the aspect usually differs from the mock**, and there the structural grid diff is reported but not gated: a correctly adapted native layout diverges from the stretched mock just as a broken one does, so the number cannot separate them. The non-reference pair is therefore still compared by eye whatever its verdict — it is the pair most likely to carry the defect.

**2. `visual-comparison` over the pairs that earned it** — one explorer subagent per screen, against a `#Preview` or a simulator screenshot:

- every pair the geometry pass marked `FAIL`;
- **one `PASS` pair per screen**, chosen as the most content-dense state;
- the **non-reference size** for every screen, whatever its verdict, because the geometry pass does not gate the grid there.

The second rule is not optional bookkeeping. The geometry pass sees geometry, not design: a wrong typeface, a mirrored icon, wrong copy, a shade under the threshold — all pass, and the script prints that list with every run. A screen whose pairs all passed mechanically has never been compared to its design.

Which concrete tool fills `visual-comparison` comes from this run's ledger; the adapters list the candidates usually registered on each agent. Its report is an artifact on disk — the subagent returns the summary and the path, per the return cap.

## Comparison rules

These bind both passes, and the second one especially:

- The style reference is the **full screenshot of the parent frame**: an isolated node export bakes in screen backgrounds and is only good for slicing assets. A bound tool that exports an isolated node by default is used against the parent-frame screenshot anyway.
- Verify Typography/Colors and other numbers from design context, not by pixel approximation.
- Mark intentional deviations coming from the resolved contract explicitly.
- Every screen is compared on at least one **non-reference** size: at the reference size a fixed canvas matches pixel-for-pixel and hides the breakage.
- An inset divergence inside the LAY-07 system-value snap window (−2…+4pt) is a match, not a defect.
- Device-frame radii in the mock are presentation chrome, not app pixels. The root render follows the system-provided shape; only an explicitly app-owned surface is compared for corner radius.
- Check relational geometry, not only absolute resemblance: a surface specified with equal left/right/bottom insets keeps those insets equal on the non-reference size (within 1pt or the equivalent screenshot-pixel tolerance).

## Fallback

- `screenshot-geometry` unavailable (no `sips`, non-macOS host) → no filter; every pair goes to `visual-comparison` and that is recorded in the gate evidence, because the stage just got more expensive, not less strict.
- `visual-comparison` unbound → manual comparison against the parent-frame screenshot under the same rules and evidence. The geometry pass never substitutes for it.
- No `FIGMA_ACCESS_TOKEN` → blocker before the stage.

## Gate

- Report on disk.
- ❌ items fixed and re-compared.
- Contract deviations explained.
- A non-reference size covered per screen.
- The geometry pass ran over every pair, with its `SCREENSHOT_DIFF_CLEAN` / `SCREENSHOT_DIFF_DIRTY` marker and report path recorded.
- Every `FAIL`, plus one `PASS` per screen, went through `visual-comparison` — named in the manifest's `Looked at by eye` column, which is never empty.

`#Preview` ≠ the flow — runtime navigation belongs to stage 7.
