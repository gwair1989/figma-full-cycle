# Adapter: Claude Code

Маппинг capability из ядра (`../SKILL.md`) на инструменты Claude Code.

## Capability map

| Capability | Claude Code |
|---|---|
| Вызов под-скилла | `Skill` tool |
| Проверка доступности Figma MCP | `ToolSearch("figma")` + реальный `get_metadata` по распарсенному parent node (сервер бывает «connecting»); записать transport и фактические capabilities; `whoami` — только при access/permission/rate-limit ошибке |
| Вопрос пользователю | `AskUserQuestion`, батч ≤4 вопросов на вызов; больше — несколько вызовов |
| Subagent explorer | `Explore` (Figma-инспекция, сверка) / `caveman:cavecrew-investigator` (поиск по коду) |
| Subagent worker | `general-purpose` с явным списком назначенных файлов |
| Worktree создать/убрать | `EnterWorktree` / `ExitWorktree` или `superpowers:using-git-worktrees` |
| Build defaults показать/задать | xcodebuildmcp `session_show_defaults` / `session_set_defaults` (сначала показать, потом менять) |
| Build / test / run | `build_sim` / `test_sim` / `build_run_sim` (сам бутит симулятор) |
| Список симуляторов | `list_sims`; в defaults задавать `simulatorId` (UDID), не имя |
| UI-инпут симулятора | `snapshot_ui` → `tap`/`swipe` по `elementRef` (координаты не принимаются) |
| Figma read acquisition | `get_metadata` один раз для карты parent; scoped `get_design_context` — primary child read; `get_screenshot`, `get_variable_defs`, optional `get_code_connect_map` / `get_motion_context` — только по evidence gaps; `download_assets` — этап 2 |
| Figma write boundary | `use_figma`, `add_code_connect_map`, `send_code_connect_mappings`, `upload_assets`, `create_new_file`, `generate_figma_design` не вызывать без отдельной явной просьбы пользователя изменить Figma |
| Compact Strings inspection | `python3 <skill-root>/scripts/localization_context.py` (read-only `inventory/lookup/diff/validate`; root — repo/owning scope) |
| UI Plan validation | `python3 <skill-root>/scripts/ui_plan.py validate --plan <PLAN> --manifest <MANIFEST> --project-root <REPO> --phase <ui|production>` |
| Финализация ветки | `superpowers:finishing-a-development-branch` — выбор (PR / merge / оставить) делает пользователь |

## Скиллы этапов

| Этап | Скилл | Fallback |
|---|---|---|
| 1 | `figma-feature-spec` | нет Figma MCP → блокер |
| 2 | `import-figma-assets` | — |
| 3 | Зарегистрированный официальный `figma-design-to-code` (включая фактический namespaced catalog alias) — обязательный workflow-prerequisite; в `skillNames` всё равно передать canonical `figma-design-to-code` либо resource-prefixed form. Зарегистрированный `figma-swiftui` — дополнительный SwiftUI translator. Затем `pfw-modern-swiftui` + `swiftui-ui-patterns` + `pfw-composable-architecture`. Context: `clientLanguages=swift`, `clientFrameworks=swiftui`; exact mapping label — только `codeConnectLabel` отдельного `get_code_connect_map` | official generic отсутствует → не подделывать `skillNames`, использовать зарегистрированный `figma-implement-design`; `figma-swiftui` отсутствует → generic/fallback + SwiftUI-скиллы проекта |
| 4 | `swiftui-view-refactor` | — |
| 5 | `design-compare` | — |
| 7 | `pfw-composable-architecture` + `pfw-testing` | не-TCA → скилл стека проекта |
| 8 | `swift-code-reviewer-skill` | `/code-review` |

## Preflight-чеклист

- [ ] До Figma-вызовов выполнен read-only аудит Strings / Typography / Colors / Images / Accessibility по `../references/project-ui-conventions.md`; пять строк контракта готовы для переноса в manifest. Для Strings сначала прочитана документация и разрешён контракт из `../references/strings-workflow.md`, затем один compact inventory без catalog dump. Accessibility без явного требования → `skill-fallback: no-add`.
- [ ] Полностью прочитан `../references/figma-mcp-acquisition.md`; transport/read capabilities/optional capabilities/target/write=`disabled` готовы для manifest.
- [ ] Figma URL локально распарсен; `fileKey` и `node-id` известны до пробного реального вызова.
- [ ] Наличие official generic и SwiftUI translator проверено независимо; зарегистрированный `figma-design-to-code` загружен до первого context call и только тогда попадает в `skillNames` (с `resource:` при MCP-resource загрузке), иначе выбран документированный fallback.
- [ ] UI Plan template/validator доступны; self-check проходит: `python3 <skill-root>/scripts/ui_plan.py validate --plan <skill-root>/templates/UI_PLAN.template.json --phase ui --allow-placeholders`.
- [ ] Figma MCP: `ToolSearch("figma")` + metadata-first вызов по parent node. Code Connect/motion недоступны → записан `degraded` fallback, а не ложный общий blocker; Figma write-tools не вызваны.
- [ ] xcodebuildmcp: `session_show_defaults` отвечает.
- [ ] `FIGMA_ACCESS_TOKEN` доступен (этап 5) — иначе записать блокером этапа 5.

Отсутствующее без fallback — одним списком в `AskUserQuestion`.
