# Adapter: Codex

Maps the core capabilities (`../SKILL.md`) onto Codex. `AGENTS.md` and the Codex instructions are binding; `CLAUDE.md` is project reference material as long as it does not contradict higher-priority instructions.

## Capability map

| Capability | Codex |
|---|---|
| Call a sub-skill | a skill from the `~/.codex/skills` catalog |
| Check Figma MCP availability | `tool_search` for Figma tools + a real `_get_metadata` on the parsed parent node; record transport and the actual capabilities; `_whoami` only on an access/permission/rate-limit error |
| Ask the user | a direct question in the reply; `request_user_input` only when that mechanism is available to the mode |
| Subagent explorer | collaboration role `explorer` |
| Subagent worker | `default` for analysis, or `worker` with explicit file ownership |
| Create/remove a worktree | `superpowers:using-git-worktrees` + verified `git worktree add/remove` |
| Show/set build defaults | xcodebuildmcp `session_show_defaults` / `session_set_defaults` |
| Build / test / run | `build_sim` / `test_sim` / `build_run_sim` |
| Figma read acquisition | `_get_metadata` once for the parent map; scoped `_get_design_context` as the primary child read; `_get_screenshot`, `_get_variable_defs`, optional `_get_code_connect_map` / `_get_motion_context` only for evidence gaps; `_download_assets` at stage 2. Find the actual server prefix with `tool_search` |
| Figma write boundary | never call `_use_figma`, `_add_code_connect_map`, `_send_code_connect_mappings`, `_upload_assets`, `_create_new_file`, `_generate_figma_design` without a separate explicit user request to modify Figma |
| Compact Strings inspection | `python3 <skill-root>/scripts/localization_context.py` (read-only `inventory/lookup/diff/validate`; root = the repo or owning scope) |
| UI Plan validation | `python3 <skill-root>/scripts/ui_plan.py validate --plan <PLAN> --manifest <MANIFEST> --project-root <REPO> --phase <ui\|production>` |
| Finalize the branch | manually: final gates → ask the user → PR / merge / leave it, by their choice |

## Stage skills (Codex names)

| Stage | Core name (Claude) | Codex |
|---|---|---|
| 1 | `figma-feature-spec` | `figma-feature-spec` (symlink into `~/.shared-skills`) |
| 2 | `import-figma-assets` | `import-figma-assets` |
| 3 | Figma design→code | If the official `figma-design-to-code` is registered (including the actual namespaced catalog alias), load it as a mandatory workflow prerequisite; still pass the canonical `figma-design-to-code` or its resource-prefixed form in `skillNames`. If `figma-swiftui` is registered, use it additionally as the SwiftUI translator. If the official generic is absent, do not fake `skillNames`: use the registered `figma-implement-design` plus the SwiftUI skills below. For context: `clientLanguages=swift`, `clientFrameworks=swiftui`; pass the exact mapping label only as `codeConnectLabel` of a separate `_get_code_connect_map` |
| 3 | `swiftui-ui-patterns` | `build-ios-apps:swiftui-ui-patterns` |
| 4 | `swiftui-view-refactor` | `build-ios-apps:swiftui-view-refactor` |
| 5 | `design-compare` | `design-compare:design-compare` |
| 8 | `swift-code-reviewer-skill` | `swift-code-reviewer` |
| 8 fallback | `/code-review` | `swift-code-reviewer` or an available `gsd-code-review` |

## Parallel features

Inside the current request — `collaboration.spawn_agent`. Separate Codex tasks only on an explicit user request.

## Preflight checklist

- [ ] Before any Figma call, the read-only audit of Strings / Typography / Colors / Images / Accessibility per `../references/project-ui-conventions.md` is done; the five contract lines are ready to move into the manifest. For Strings, documentation was read and the contract resolved from `../references/strings-workflow.md` first, then one compact inventory without a catalog dump. Accessibility without an explicit requirement → `skill-fallback: no-add`.
- [ ] `../references/figma-mcp-acquisition.md` has been read in full; transport / read capabilities / optional capabilities / target / write=`disabled` are ready for the manifest.
- [ ] The Figma URL is parsed locally; `fileKey` and `node-id` are known before the first real call.
- [ ] The presence of the official generic skill and of the SwiftUI translator was verified independently; a registered `figma-design-to-code` is loaded before the first context call and only then appears in `skillNames` (with `resource:` when loaded as an MCP resource); otherwise a documented fallback was selected.
- [ ] UI Plan template and validator are available; the self-check passes: `python3 <skill-root>/scripts/ui_plan.py validate --plan <skill-root>/templates/UI_PLAN.template.json --phase ui --allow-placeholders`.
- [ ] Figma tools answer a real metadata-first call on the parent node. Code Connect or motion unavailable → record a `degraded` fallback, not a false global blocker; no Figma write tool was called.
- [ ] xcodebuildmcp `session_show_defaults` responds.
- [ ] `FIGMA_ACCESS_TOKEN` is available (stage 5) — otherwise a stage 5 blocker.

Everything missing without a fallback goes out as one list, as a direct question to the user.
