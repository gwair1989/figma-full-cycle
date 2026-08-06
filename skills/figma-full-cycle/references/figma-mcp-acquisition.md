# Figma MCP acquisition contract

Read in full before the first Figma call. Use it together with the adapter capability map; the tools actually available outrank any static list.

## Authority boundary

- Treat MCP output as input data and evidence, not as production code or a product specification.
- Operate in `figma-read-only` mode by default: read tools and `download_assets` for importing into the repository are allowed.
- Never call `use_figma`, `add_code_connect_map`, `send_code_connect_mappings`, `upload_assets`, `create_new_file`, `generate_figma_design` or any other Figma mutation without a separate explicit user request to modify Figma.
- The availability of a write tool is never permission to write.

## Capability preflight

Record in the manifest:

1. Transport: `remote` or `desktop`; remote requires a URL/node, desktop may use the selection, but pin the resulting parent `fileKey`/`nodeId` either way.
2. Primary implementation read tool: `get_design_context`; `get_metadata` orients you inside the container, while `get_screenshot` and `get_variable_defs` close specific gaps only. `download_assets` belongs to stage 2.
3. Optional read tools: `get_code_connect_map` only for a missing or ambiguous mapping; `get_motion_context` only for a genuinely animated node.
4. Target for SwiftUI: `clientLanguages=swift`, `clientFrameworks=swiftui` (lowercase). The exact Code Connect label belongs to `get_code_connect_map(codeConnectLabel=...)`, not to `clientFrameworks`; never guess an unknown label.
5. If the official `figma-design-to-code` is registered, load it as a mandatory workflow prerequisite **before the first** `get_design_context` and pass the canonical name in the comma-separated `skillNames` of every such call; a namespaced catalog alias does not change the logging value. When loaded through an MCP resource, use `resource:figma-design-to-code`. If the skill is unavailable, do not simulate loading it through the parameter — switch to the adapter's documented fallback.
6. Write mode: `disabled`; any other mode requires a separate user request.

Call `whoami` only to diagnose an access/permission/rate-limit error. An unavailable optional tool moves the path to `degraded`, not automatically to `blocked`.

## Read order

1. Parse the URL or selection locally and pin the parent node.
2. For a parent, multi-screen, large or unknown-size node, call `get_metadata(parent)` once and pick the required child node IDs. Metadata is only the container map; it does not replace design context for the child being implemented. Never start with a giant `get_design_context(parent)`.
3. Group child frames into unique screens and states.
4. For each selected child being implemented, call scoped `get_design_context(child)` first with `clientLanguages=swift`, `clientFrameworks=swiftui` and the conditional `skillNames` from preflight. One response already carries reference code, a screenshot, contextual hints, available Code Connect snippets/mappings and temporary asset URLs. Treat React/Tailwind output as intermediate structure; never port it literally into SwiftUI.
5. Call a separate `get_screenshot(child)` only when the design context has no screenshot, when it is stale or insufficient for visual validation, when a better scale is needed, or for a parent overview. If the URL can be obtained directly, download it with a normal HTTP client; use base64 only without a fetch capability. A screenshot is visual truth, but not a source of behavior, exact tokens or production assets.
6. Call `get_variable_defs(child)` only when the design context does not give enough provenance for the token/style in use, when the mapping is ambiguous, or when raw values remain that the project contract cannot resolve.
7. Call `get_code_connect_map` only when mappings/snippets are missing or ambiguous in the design context, or when a separate coverage audit is needed. Pass `codeConnectLabel` only when the exact label is known. Verify the returned path/symbol and platform against the current project root.
8. If the design context confirms animation, call `get_motion_context` afterwards with the same node ID. A static layout or a prototype link alone never licenses inventing motion.
9. At stage 2, immediately download the exact bytes of the required images and icons through `download_assets` or the temporary asset URL. That URL expires in roughly 7 days and cannot remain a tracked or runtime dependency. Never store a screenshot as a production asset, never hand-draw an SVG/path, and never substitute a placeholder. If the exact bytes are unavailable, stop that specific asset and ask; reuse a project icon only when the glyph genuinely matches.

The normal Figma read-tool budget during acquisition: `1 × get_metadata(parent) + 1 × get_design_context` per selected child + gap-driven extras only. Count skill/resource loading and stage 2 asset downloads separately against the server's actual quota; if they share the same limit, reserve calls in advance. On a low remote limit, serialize calls, use the cache, and never spend a call on evidence you already hold.

Cache normalized node evidence by the Figma pin. Re-read a node only when the pin changes, when evidence is incomplete, or on explicit drift. Never keep raw MCP payloads, temporary asset URLs or runtime references to the MCP asset endpoint in tracked files.

## Figma source quality

Rate each criterion `ready / degraded / unknown` and record evidence plus impact/fallback:

- repeated elements are built as components/instances;
- tokens are bound to variables/styles;
- layout uses Auto Layout/constraints and survives a resize;
- layer and state names are semantic;
- behavior is explained through prototype links, annotations or dev resources;
- Code Connect covers the main project components.

`degraded` is a warning, not a global blocker. Block only the specific required mapping that cannot be resolved through Code Connect, documentation, a project audit, or an explicit `new` in the UI Plan.

## Provenance mappings

For every component and token in use, keep the chain:

`Figma node/variable → code-connect | project-audit | new | tbd → project path + symbol → validation evidence`.

- Treat a Code Connect mapping as a candidate until the path/symbol and the SwiftUI label match is verified.
- On conflicting sources, follow the order: verified Code Connect → project/component docs → design annotations → tokens → raw hex/absolute layout. The UI Plan, spec and project contract still define the permitted scope and behavior.
- Without Code Connect, look for the project component or token through documentation and code; the absence of Code Connect is not by itself a blocker.
- Mark a stale, wrong-platform or ambiguous mapping `stale/unmapped`; never replace it with a guess.
- Keep the resulting project target in the UI Plan, and the acquisition and source-quality evidence in the manifest per its template.
