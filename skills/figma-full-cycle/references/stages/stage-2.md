# Stage 2 — Assets

**Read before starting:** nothing beyond the resolved Images and Accessibility contract rows. The vector/raster, catalog/namespace and rendering-intent rules live in the sub-skill, not here.

## Role binding

`asset-import` (pinned `import-figma-assets`) against the node-id inventory from the spec and the resolved Images contract line.

- Accessibility-specific image variants and labels obey the Accessibility contract and are not created under `no-add`.
- Check SVG exports for a baked-in frame background (rect or gradient backdrop) — cut it before the imageset.

## Fallback

None. The sub-skill is pinned.

## Gate

- Build succeeds.
- Every asset is `done` in the checklist (exists, size/hash).
- Images and Accessibility contracts respected.
