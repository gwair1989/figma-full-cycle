---
name: import-figma-assets
description: Import Figma assets into Apple Xcode projects while preserving vector artwork and generating complete 1x/2x/3x raster image sets. Use when implementing iOS, iPadOS, macOS, watchOS, tvOS, or visionOS UI from a Figma URL or node ID; downloading PNG, SVG, or PDF resources from Figma; creating or updating Assets.xcassets image sets; or wiring Figma artwork into SwiftUI, UIKit, or AppKit code.
---

# Import Figma Assets

Import production artwork from an exact Figma node into an existing Xcode asset catalog. Preserve vectors as vectors; derive raster variants from one verified 3x PNG.

## Follow the required flow

1. Load the Figma workflow skill your agent's catalog actually registers before calling Figma tools, and follow its required context-first workflow. Take the name from the live catalog, not from memory; inside `figma-full-cycle`, reuse the `design-to-code-workflow` binding already recorded in the capability ledger. Tool names below (`get_design_context`, `get_screenshot`, `download_assets`) are the Figma MCP defaults — use the actual registered names when the server prefixes or renames them.
2. Inspect the repository before downloading anything:
   - Locate the relevant `.xcodeproj` or `.xcworkspace`, target, platform, and existing `Assets.xcassets` catalogs.
   - Follow the project's existing asset naming, rendering-mode, namespace, and code-access conventions.
   - Search all catalogs assigned to the target for the intended qualified asset name. Treat namespace-providing groups as part of the runtime name.
3. Fetch the exact Figma node with `get_design_context`. If truncated, fetch metadata and then the smallest exact node. Fetch `get_screenshot` before downloading assets.
4. Classify each production asset as vector, raster, or mixed before exporting it.
5. Download only the exact assets used by the implementation. Never use the inspection screenshot as a production asset.
6. Create or update the image set, reference its catalog name from UI code, build the affected target, and compare the result with the Figma screenshot.

## Classify and export

### Vector

Treat artwork as vector only when its production representation has no bitmap image fill and Figma can export it faithfully as SVG or PDF. Export at 1x, preserve vector data, and do not create raster scale variants.

Prefer the vector format already used by the project. If the project has no convention, prefer SVG when the target's Xcode/deployment setup supports it; otherwise use PDF.

### Raster

Treat PNG artwork, bitmap image fills, photos, and effects that require flattening as raster. Call `download_assets` for the exact node with both `defaultFormat: "png"` and `defaultScale: 3`; this installed skill represents the user's standing request to override node export settings with a 3x PNG production render.

Before running the generator, verify that the returned exported render is PNG and that each pixel dimension matches the Figma logical bound multiplied by three, allowing at most one pixel of rounding per axis. If format or dimensions do not match, do not interpret the file as 3x: retry the exact export once, then stop with the mismatch rather than producing mislabeled scale variants.

Use the exported node render, not an arbitrary raw uploaded source. Use a raw source image only when all of these are true:

- It is the intended production layer without surrounding layout or effects.
- Its pixel dimensions match the Figma logical bounds multiplied by three, allowing at most one pixel of rounding per axis.
- Using it preserves the appearance shown in the Figma screenshot.

Verify dimensions before generation. Fractional Figma bounds may produce a dimension not divisible by three; the bundled generator adjusts only the canvas to the nearest divisible dimension with a maximum one-pixel crop or transparent pad per axis. It must not resample or geometrically distort the 3x artwork during this normalization.

### Mixed

Treat a node containing vectors plus bitmap content, raster-only effects, or clipping that must remain visually fused as raster and export the complete node at 3x. Keep independently reusable vector children separate only when the implementation uses them separately.

## Create the Xcode image set

Download exported files into a temporary directory, not into the repository root. Choose the existing catalog assigned to the affected target, then run the bundled generator from this skill directory:

```zsh
scripts/generate_xcode_imageset.zsh \
  --input "/absolute/path/to/exported-file" \
  --catalog "/absolute/path/to/Assets.xcassets" \
  --name "projectAssetName"
```

When the catalog uses an existing group directory, pass its path relative to the catalog:

```zsh
scripts/generate_xcode_imageset.zsh \
  --input "/absolute/path/to/exported-file" \
  --catalog "/absolute/path/to/Assets.xcassets" \
  --group "Feature/Artwork" \
  --name "projectAssetName"
```

Never create or guess a group solely to organize this import. Reuse an existing group and inspect its `Contents.json` plus ancestor groups to determine whether it provides a namespace.

For PNG input, treat the input as 3x and create:

- `projectAssetName.png` at 1x
- `projectAssetName@2x.png` at 2x
- `projectAssetName@3x.png` at 3x
- `Contents.json` with universal 1x, 2x, and 3x slots

For SVG or PDF input, copy one 1x vector file and create `Contents.json` with vector preservation enabled.

Set rendering intent explicitly when the design or project convention requires it:

- Pass `--rendering-intent template` for a monochrome tintable asset.
- Pass `--rendering-intent original` for artwork that must retain its colors.
- Omit the option to preserve Xcode's default behavior. During a safe replacement, inherit a supported existing intent when the option is omitted.

If the Figma design supplies light, dark, high-contrast, language-direction, device, or other appearance variants, do not collapse them into this one-input generator. Build the complete variant image set by following the project's existing catalog structure, then validate every slot and build the target.

The generator refuses to overwrite an existing `.imageset`. Inspect the existing asset and its references first. Pass `--replace` only when replacement is within the user's requested change and the chosen catalog and asset name have been verified. Replacement is allowed only for a plain image set shaped like this generator's output, optionally with a supported rendering intent. The generator must refuse appearances, localization, compression settings, device variants, other metadata, or untracked files so nothing can be silently discarded.

## Wire the asset into code

Reference the catalog name without scale suffixes or file extensions. Use the project's qualified name or generated accessor when an ancestor group provides a namespace; otherwise use the plain asset name:

- SwiftUI: `Image("projectAssetName")`
- UIKit: `UIImage(named: "projectAssetName")`
- AppKit: `NSImage(named: "projectAssetName")`

Reuse generated asset-symbol accessors when the project enables them. Preserve template/original rendering behavior and accessibility labels from the existing design and project conventions.

## Validate before completion

- Confirm `Contents.json` parses and every referenced filename exists.
- Confirm raster dimensions have an exact 1:2:3 relationship and retain transparency when present.
- Confirm vectors remain a single vector representation.
- Confirm no conflicting qualified asset name exists in another catalog assigned to the target.
- Build the affected scheme or target and resolve asset-catalog warnings or errors.
- Compare the rendered UI with the exact Figma screenshot at relevant appearances and device scales.
- Remove temporary downloads after successful verification.

## Guardrails

Do not rasterize vector artwork merely to create scale slots. Do not use this generic image-set workflow for app icons, launch images, symbol sets, stickers, complications, nine-slice/cap-inset resources, or other assets requiring specialized metadata. Do not automatically create three large copies of photographs or full-screen backgrounds unless the design uses them as fixed-size bitmap UI resources and the size tradeoff is acceptable.
