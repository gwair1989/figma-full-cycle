# Adapter: Claude Code

Maps the core capabilities (`../SKILL.md`) onto Claude Code tools.

## Capability map

| Capability | Claude Code |
|---|---|
| Call a sub-skill | `Skill` tool, with the name exactly as registered (plugin entries keep their `plugin:skill` prefix, directory-scoped ones their path prefix) |
| Enumerate skills | the session's available-skills listing + the user-invocable slash commands; never guess a name that is not there |
| Enumerate MCP tools | `ToolSearch` per role keyword (`"figma"`, `"simulator build"`, `"review"`, …); deferred tools are loaded by `select:<name>` before the first call; a server listed as needing authentication counts as unavailable until it is authorized |
| Enumerate MCP resources / plugins | `ListMcpResourcesTool` / `ReadMcpResourceTool` for skills served as resources; plugin skills appear prefixed in the skills listing |
| Check Figma MCP availability | `ToolSearch("figma")` → one `whoami` as the auth probe → a real `get_metadata` on the parsed parent node (the server is sometimes "connecting"); record transport, identity and the actual capabilities in the ledger |
| Ask the user | `AskUserQuestion`, batches of ≤4 questions per call; more than that → several calls |
| Subagent explorer | `Explore` (Figma inspection, comparison) / `caveman:cavecrew-investigator` (code search) |
| Subagent worker | `general-purpose` with an explicit list of assigned files |
| Create/remove a worktree | `EnterWorktree` / `ExitWorktree` or `superpowers:using-git-worktrees` |
| Show/set build defaults | xcodebuildmcp `session_show_defaults` / `session_set_defaults` (show first, then change) |
| Build / test / run | `build_sim` / `test_sim` / `build_run_sim` (boots the simulator itself) |
| List simulators | `list_sims`; set `simulatorId` (UDID) in defaults, never a name |
| Simulator UI input | `snapshot_ui` → `tap`/`swipe` by `elementRef` (coordinates are not accepted) |
| Physical iPhone control | bundled `device-usage` via its discovered name; use available desktop Computer Use and the skill's CLI workflow, never simulator-only input tools |
| Figma read acquisition | `get_metadata` once for the parent map; scoped `get_design_context` as the primary child read; `get_screenshot`, `get_variable_defs`, optional `get_code_connect_map` / `get_motion_context` only for evidence gaps; `download_assets` at stage 2 |
| Figma write boundary | never call `use_figma`, `add_code_connect_map`, `send_code_connect_mappings`, `upload_assets`, `create_new_file`, `generate_figma_design` without a separate explicit user request to modify Figma |
| Compact Strings inspection | `python3 <skill-root>/scripts/localization_context.py` (read-only `inventory/lookup/diff/validate`; root = the repo or owning scope) |
| UI Plan validation | `python3 <skill-root>/scripts/ui_plan.py validate --plan <PLAN> --manifest <MANIFEST> --project-root <REPO> --phase <ui\|production>` |
| Finalize the branch | `superpowers:finishing-a-development-branch` — the user makes the choice (PR / merge / leave it) |

## Role bindings

Roles come from `../references/capability-discovery.md`. Only the pinned rows are fixed; every other row lists **candidates commonly registered in a Claude Code catalog** — verify each against this run's listing before use, and bind a better-matching or newer entry when the sweep finds one.

| Stage | Role | Candidates seen in Claude Code catalogs | Fallback |
|---|---|---|---|
| 1 | `feature-spec` | pinned `figma-feature-spec` | — |
| 1, 2, 3, 5 | `design-source-read` | the Figma MCP toolset | no read path → blocker |
| 2 | `asset-import` | pinned `import-figma-assets` | — |
| 5–7, physical scope only | `physical-device-control` | bundled `device-usage`, exact registered name | report unavailable control; required physical UI checks stay blocked |
| 1, 3 | `design-to-code-workflow` | the official Figma design→code skill, however it is registered (plain, namespaced `figma:…`, or `resource:…`) | absent → do not fake `skillNames`; use the registered generic implementation skill (`figma-implement-design` and the like) |
| 3 | `platform-design-translator` | an official SwiftUI-specific Figma translator (`figma-swiftui` and the like) | generic binding + the project's UI skills |
| 3, 4 | `platform-ui-idiom` | `pfw-modern-swiftui`, `swiftui-ui-patterns` | project documentation + precedent |
| 3, 7 | `app-architecture` | a discovered skill matching the documented or user-confirmed project architecture | implement the resolved architecture contract directly; unresolved → ask the user |
| 4 | `view-refactor` | `swiftui-view-refactor` | skip the conditional stage, record why |
| 5 | `visual-comparison` | `design-compare` | manual comparison under the stage 5 rules |
| 7 | `test-authoring` | `pfw-testing` | the project's test conventions |
| 8 | `code-review` | `swift-code-reviewer-skill` | `/code-review`, else the built-in review path |
| 0, 3, 5–8 | `build-run` | xcodebuildmcp | the project's own build commands |

Stage 3 context stays `clientLanguages=swift`, `clientFrameworks=swiftui`; the exact mapping label goes only into `codeConnectLabel` of a separate `get_code_connect_map`.

## Preflight checklist

- [ ] Project architecture is resolved from applicable documentation or an explicit user decision and ready for the manifest. Missing, ambiguous or contradictory documentation was raised with the user; code and installed skills did not choose the architecture. Bind `app-architecture` only after this resolution, including in `ui-first`.
- [ ] `../references/capability-discovery.md` has been read in full; the sweep ran over skills / MCP tools / MCP resources / plugins / project-local scripts, and every role is bound, fallen back, or listed in the single blocker batch.
- [ ] Before any Figma call, the read-only audit of Strings / Typography / Colors / Images / Accessibility per `../references/project-ui-conventions.md` is done; the five contract lines are ready to move into the manifest. For Strings, documentation was read and the contract resolved from `../references/strings-workflow.md` first, then one compact inventory without a catalog dump. Accessibility without an explicit requirement → `skill-fallback: no-add`.
- [ ] `../references/figma-mcp-acquisition.md` has been read in full; transport / read capabilities / optional capabilities / target / write=`disabled` are ready for the manifest.
- [ ] The Figma URL is parsed locally; `fileKey` and `node-id` are known before the first real call.
- [ ] `design-to-code-workflow` and `platform-design-translator` were resolved independently against the live listing; the bound workflow skill is loaded before the first context call and only then appears in `skillNames`, spelled exactly as registered (with `resource:` when loaded as an MCP resource); otherwise a documented fallback was selected.
- [ ] UI Plan template and validator are available; the self-check passes: `python3 <skill-root>/scripts/ui_plan.py validate --plan <skill-root>/templates/UI_PLAN.template.json --phase ui --allow-placeholders`.
- [ ] Figma MCP: `ToolSearch("figma")` → `whoami` auth probe → a metadata-first call on the parent node, with the failure cause distinguished (auth / permission / node / transport). Code Connect or motion unavailable → record a `degraded` fallback, not a false global blocker; no Figma write tool was called.
- [ ] xcodebuildmcp: `session_show_defaults` responds.
- [ ] `FIGMA_ACCESS_TOKEN` is available (stage 5) — otherwise record it as a stage 5 blocker.

Everything missing without a fallback goes out as one list in `AskUserQuestion`.
