# Adapter: Codex

Maps the core capabilities (`../SKILL.md`) onto Codex. `AGENTS.md` and the Codex instructions are binding; `CLAUDE.md` is project reference material as long as it does not contradict higher-priority instructions.

## Capability map

| Capability | Codex |
|---|---|
| Call a sub-skill | a skill from the current session's live catalog, by its exact registered name; bundled identities keep the plugin namespace when registered that way |
| Enumerate skills | use the session's available-skills catalog first, including plugins; inspect configured user/project skill directories and plugin resources only to resolve missing metadata, never assume one installation path |
| Enumerate MCP tools / servers | `tool_search` per role keyword; the configured servers in the Codex MCP configuration; a server that does not answer counts as unavailable |
| Enumerate project-local tooling | `AGENTS.md`, project docs, `Makefile` / scripts in the repository |
| Check Figma MCP availability | `tool_search` for Figma tools → one `_whoami` as the auth probe → a real `_get_metadata` on the parsed parent node; record transport, identity and the actual capabilities in the ledger |
| Ask the user | a direct question in the reply; `request_user_input` only when that mechanism is available to the mode |
| Subagent explorer | collaboration role `explorer` |
| Subagent worker | `default` for analysis, or `worker` with explicit file ownership |
| Create/remove a worktree | `superpowers:using-git-worktrees` + verified `git worktree add/remove` |
| Show/set build defaults | xcodebuildmcp `session_show_defaults` / `session_set_defaults` |
| Build / test / run | `build_sim` / `test_sim` / `build_run_sim` |
| Physical iPhone control | bundled `device-usage` via its discovered name; Device Hub through available desktop Computer Use, with device CLI diagnostics per that skill; never pass physical IDs to simulator tools |
| Figma read acquisition | `_get_metadata` once for the parent map; scoped `_get_design_context` as the primary child read; `_get_screenshot`, `_get_variable_defs`, optional `_get_code_connect_map` / `_get_motion_context` only for evidence gaps; `_download_assets` at stage 2. Find the actual server prefix with `tool_search` |
| Figma write boundary | never call `_use_figma`, `_add_code_connect_map`, `_send_code_connect_mappings`, `_upload_assets`, `_create_new_file`, `_generate_figma_design` without a separate explicit user request to modify Figma |
| Compact Strings inspection | `python3 <shared-root>/scripts/localization_context.py` (read-only `inventory/lookup/diff/validate`; root = the repo or owning scope) |
| UI Plan validation | `python3 <skill-root>/scripts/ui_plan.py validate --plan <PLAN> --manifest <MANIFEST> --project-root <REPO> --phase <ui\|production>` |
| Finalize the branch | manually: final gates → ask the user → PR / merge / leave it, by their choice |

## Role bindings (Codex names)

Roles come from `../references/capability-discovery.md`. Only the pinned identities are fixed; the rest are **candidates seen in Codex catalogs**, where namespacing differs from Claude Code. Verify each against the live session catalog, including plugin entries, and bind whatever covers the role best this run.

| Stage | Role | Candidates seen in Codex catalogs | Fallback |
|---|---|---|---|
| 1 | `feature-spec` | bundled `figma-feature-spec`, exact registered name | — |
| 2 | `asset-import` | pinned `import-figma-assets` | — |
| 5–7, physical scope only | `physical-device-control` | bundled `device-usage`, exact registered name | report unavailable control; required physical UI checks stay blocked |
| 1, 3 | `design-to-code-workflow` | the official Figma design→code skill under its catalog name or namespaced alias | absent → do not fake `skillNames`; use the registered generic implementation skill (`figma-implement-design` and the like) |
| 3 | `platform-design-translator` | an official SwiftUI-specific Figma translator | generic binding + the UI skills below |
| 3, 4 | `platform-ui-idiom` | `build-ios-apps:swiftui-ui-patterns` | project documentation + precedent |
| 4 | `view-refactor` | `build-ios-apps:swiftui-view-refactor` | skip the conditional stage, record why |
| 5 | `visual-comparison` | bundled `figma-design-compare`, exact registered name | missing companion is a blocker; its internal reviewer fallback remains available |
| 6 | `adaptivity-check` | bundled `swiftui-adaptivity-check`, exact registered name | missing companion is a blocker |
| 3, 7 | `app-architecture` | a discovered skill matching the documented or user-confirmed project architecture | implement the resolved architecture contract directly; unresolved → ask the user |
| 7 | `test-authoring` | the stack's testing skill | the project's test conventions |
| 8 | `code-review` | `swift-code-reviewer` | an available `gsd-code-review`, else a manual review pass |
| 0, 3, 5–8 | `build-run` | xcodebuildmcp | the project's own build commands |

Stage 3 context stays `clientLanguages=swift`, `clientFrameworks=swiftui`; pass the exact mapping label only as `codeConnectLabel` of a separate `_get_code_connect_map`.

## Parallel features

Inside the current request — `collaboration.spawn_agent`. Separate Codex tasks only on an explicit user request.

## Preflight checklist

- [ ] Project architecture is resolved from applicable documentation or an explicit user decision and ready for the manifest. Missing, ambiguous or contradictory documentation was raised with the user; code and installed skills did not choose the architecture. Bind `app-architecture` only after this resolution, including in `ui-first`.
- [ ] `../references/capability-discovery.md` has been read in full; the sweep ran over the skills catalog / MCP tools / project-local tooling, and every role is bound, fallen back, or listed in the single blocker batch.
- [ ] Before any Figma call, the read-only audit of Layout / Strings / Typography / Colors / Images / Accessibility per `<shared-root>/references/project-ui-conventions.md` is done; the six contract lines are ready to move into the manifest. For Strings, documentation was read and the contract resolved from the shared convention baseline first, then one compact inventory without a catalog dump. Accessibility without an explicit requirement → `skill-fallback: no-add`.
- [ ] `<shared-root>/references/figma-mcp-acquisition.md` has been read in full; transport / read capabilities / optional capabilities / target / write=`disabled` are ready for the manifest.
- [ ] The Figma URL is parsed locally; `fileKey` and `node-id` are known before the first real call.
- [ ] `design-to-code-workflow` and `platform-design-translator` were resolved independently against the live catalog; the bound workflow skill is loaded before the first context call and only then appears in `skillNames`, spelled exactly as registered (with `resource:` when loaded as an MCP resource); otherwise a documented fallback was selected.
- [ ] UI Plan template and validator are available; the self-check passes: `python3 <skill-root>/scripts/ui_plan.py validate --plan <skill-root>/templates/UI_PLAN.template.json --phase ui --allow-placeholders`.
- [ ] Figma tools answer the `_whoami` auth probe and a real metadata-first call on the parent node, with the failure cause distinguished (auth / permission / node / transport). Code Connect or motion unavailable → record a `degraded` fallback, not a false global blocker; no Figma write tool was called.
- [ ] xcodebuildmcp `session_show_defaults` responds.
- [ ] `FIGMA_ACCESS_TOKEN` is available (stage 5) — otherwise a stage 5 blocker.

Everything missing without a fallback goes out as one list, as a direct question to the user.
