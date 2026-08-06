# Adapter: Claude Code

Maps the core capabilities (`../SKILL.md`) onto Claude Code tools.

## Capability map

| Capability | Claude Code |
|---|---|
| Call a sub-skill | `Skill` tool |
| Check Figma MCP availability | `ToolSearch("figma")` + a real `get_metadata` on the parsed parent node (the server is sometimes "connecting"); record transport and the actual capabilities; `whoami` only on an access/permission/rate-limit error |
| Ask the user | `AskUserQuestion`, batches of ≤4 questions per call; more than that → several calls |
| Subagent explorer | `Explore` (Figma inspection, comparison) / `caveman:cavecrew-investigator` (code search) |
| Subagent worker | `general-purpose` with an explicit list of assigned files |
| Create/remove a worktree | `EnterWorktree` / `ExitWorktree` or `superpowers:using-git-worktrees` |
| Show/set build defaults | xcodebuildmcp `session_show_defaults` / `session_set_defaults` (show first, then change) |
| Build / test / run | `build_sim` / `test_sim` / `build_run_sim` (boots the simulator itself) |
| List simulators | `list_sims`; set `simulatorId` (UDID) in defaults, never a name |
| Simulator UI input | `snapshot_ui` → `tap`/`swipe` by `elementRef` (coordinates are not accepted) |
| Figma read acquisition | `get_metadata` once for the parent map; scoped `get_design_context` as the primary child read; `get_screenshot`, `get_variable_defs`, optional `get_code_connect_map` / `get_motion_context` only for evidence gaps; `download_assets` at stage 2 |
| Figma write boundary | never call `use_figma`, `add_code_connect_map`, `send_code_connect_mappings`, `upload_assets`, `create_new_file`, `generate_figma_design` without a separate explicit user request to modify Figma |
| Compact Strings inspection | `python3 <skill-root>/scripts/localization_context.py` (read-only `inventory/lookup/diff/validate`; root = the repo or owning scope) |
| UI Plan validation | `python3 <skill-root>/scripts/ui_plan.py validate --plan <PLAN> --manifest <MANIFEST> --project-root <REPO> --phase <ui\|production>` |
| Finalize the branch | `superpowers:finishing-a-development-branch` — the user makes the choice (PR / merge / leave it) |

## Stage skills

| Stage | Skill | Fallback |
|---|---|---|
| 1 | `figma-feature-spec` | no Figma MCP → blocker |
| 2 | `import-figma-assets` | — |
| 3 | The registered official `figma-design-to-code` (including the actual namespaced catalog alias) is a mandatory workflow prerequisite; still pass the canonical `figma-design-to-code` or its resource-prefixed form in `skillNames`. A registered `figma-swiftui` is an additional SwiftUI translator. Then `pfw-modern-swiftui` + `swiftui-ui-patterns` + `pfw-composable-architecture`. Context: `clientLanguages=swift`, `clientFrameworks=swiftui`; the exact mapping label goes only into `codeConnectLabel` of a separate `get_code_connect_map` | no official generic → do not fake `skillNames`, use the registered `figma-implement-design`; no `figma-swiftui` → generic/fallback + the project's SwiftUI skills |
| 4 | `swiftui-view-refactor` | — |
| 5 | `design-compare` | — |
| 7 | `pfw-composable-architecture` + `pfw-testing` | non-TCA → the project's stack skill |
| 8 | `swift-code-reviewer-skill` | `/code-review` |

## Preflight checklist

- [ ] Before any Figma call, the read-only audit of Strings / Typography / Colors / Images / Accessibility per `../references/project-ui-conventions.md` is done; the five contract lines are ready to move into the manifest. For Strings, documentation was read and the contract resolved from `../references/strings-workflow.md` first, then one compact inventory without a catalog dump. Accessibility without an explicit requirement → `skill-fallback: no-add`.
- [ ] `../references/figma-mcp-acquisition.md` has been read in full; transport / read capabilities / optional capabilities / target / write=`disabled` are ready for the manifest.
- [ ] The Figma URL is parsed locally; `fileKey` and `node-id` are known before the first real call.
- [ ] The presence of the official generic skill and of the SwiftUI translator was verified independently; a registered `figma-design-to-code` is loaded before the first context call and only then appears in `skillNames` (with `resource:` when loaded as an MCP resource); otherwise a documented fallback was selected.
- [ ] UI Plan template and validator are available; the self-check passes: `python3 <skill-root>/scripts/ui_plan.py validate --plan <skill-root>/templates/UI_PLAN.template.json --phase ui --allow-placeholders`.
- [ ] Figma MCP: `ToolSearch("figma")` + a metadata-first call on the parent node. Code Connect or motion unavailable → record a `degraded` fallback, not a false global blocker; no Figma write tool was called.
- [ ] xcodebuildmcp: `session_show_defaults` responds.
- [ ] `FIGMA_ACCESS_TOKEN` is available (stage 5) — otherwise record it as a stage 5 blocker.

Everything missing without a fallback goes out as one list in `AskUserQuestion`.
