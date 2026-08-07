# Stage 5 — Design comparison

**Read before starting** (skip what the session already holds): the LAY-07 snap window and §3 of [`../layout-adaptivity-contract.md`](../layout-adaptivity-contract.md); COL-06 of [`../colors-contract.md`](../colors-contract.md). Both are normally still in session from stage 3.

## Role binding

Re-check the Figma pin, then `visual-comparison` per screen (`#Preview` or a simulator screenshot; one explorer subagent per screen).

- The style reference is the **full screenshot of the parent frame**: an isolated node export bakes in screen backgrounds and is only good for slicing assets.
- Verify Typography/Colors and other numbers from design context, not by pixel approximation.
- Mark intentional deviations coming from the resolved contract explicitly.
- Compare every screen on at least one **non-reference** size as well: at the reference size a fixed canvas matches pixel-for-pixel and hides the breakage.
- An inset divergence inside the LAY-07 system-value snap window (−2…+4pt) is a match, not a defect.

## Fallback

- `visual-comparison` unbound → manual comparison against the parent-frame screenshot under the same rules and evidence.
- No `FIGMA_ACCESS_TOKEN` → blocker before the stage.

## Gate

- Report on disk.
- ❌ items fixed and re-compared.
- Contract deviations explained.
- A non-reference size covered per screen.

`#Preview` ≠ the flow — runtime navigation belongs to stage 7.
