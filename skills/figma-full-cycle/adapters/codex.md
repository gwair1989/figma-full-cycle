# Adapter: Codex

Маппинг capability из ядра (`../SKILL.md`) на Codex. `AGENTS.md` и инструкции Codex обязательны; `CLAUDE.md` — проектная справка, если не противоречит инструкциям более высокого приоритета.

## Capability map

| Capability | Codex |
|---|---|
| Вызов под-скилла | скилл из каталога `~/.codex/skills` |
| Проверка доступности Figma MCP | `tool_search` по Figma tools + реальный `_get_metadata` по распарсенному parent node; записать transport и фактические capabilities; `_whoami` — только при access/permission/rate-limit ошибке |
| Вопрос пользователю | прямой вопрос в ответе; `request_user_input` — только когда этот механизм доступен режиму |
| Subagent explorer | collaboration role `explorer` |
| Subagent worker | `default` для анализа или `worker` с явным владением файлами |
| Worktree создать/убрать | `superpowers:using-git-worktrees` + проверенные `git worktree add/remove` |
| Build defaults показать/задать | xcodebuildmcp `session_show_defaults` / `session_set_defaults` |
| Build / test / run | `build_sim` / `test_sim` / `build_run_sim` |
| Figma read acquisition | `_get_metadata` один раз для карты parent; scoped `_get_design_context` — primary child read; `_get_screenshot`, `_get_variable_defs`, optional `_get_code_connect_map` / `_get_motion_context` — только по evidence gaps; `_download_assets` — этап 2. Конкретный server prefix найти через `tool_search` |
| Figma write boundary | `_use_figma`, `_add_code_connect_map`, `_send_code_connect_mappings`, `_upload_assets`, `_create_new_file`, `_generate_figma_design` не вызывать без отдельной явной просьбы пользователя изменить Figma |
| Compact Strings inspection | `python3 <skill-root>/scripts/localization_context.py` (read-only `inventory/lookup/diff/validate`; root — repo/owning scope) |
| UI Plan validation | `python3 <skill-root>/scripts/ui_plan.py validate --plan <PLAN> --manifest <MANIFEST> --project-root <REPO> --phase <ui|production>` |
| Финализация ветки | вручную: final gates → вопрос пользователю → PR / merge / оставить по его выбору |

## Скиллы этапов (Codex-имена)

| Этап | Имя в ядре (Claude) | Codex |
|---|---|---|
| 1 | `figma-feature-spec` | `figma-feature-spec` (symlink на `~/.shared-skills`) |
| 2 | `import-figma-assets` | `import-figma-assets` |
| 3 | Figma design→code | Если зарегистрирован официальный `figma-design-to-code` (включая фактический namespaced catalog alias), загрузить его обязательным workflow-prerequisite; в `skillNames` всё равно передать canonical `figma-design-to-code` либо resource-prefixed form. Если зарегистрирован `figma-swiftui`, использовать дополнительно как SwiftUI translator. Если official generic отсутствует, не подделывать `skillNames`: использовать зарегистрированный `figma-implement-design` и SwiftUI-скиллы ниже. Для context: `clientLanguages=swift`, `clientFrameworks=swiftui`; exact mapping label передавать только как `codeConnectLabel` отдельного `_get_code_connect_map` |
| 3 | `swiftui-ui-patterns` | `build-ios-apps:swiftui-ui-patterns` |
| 4 | `swiftui-view-refactor` | `build-ios-apps:swiftui-view-refactor` |
| 5 | `design-compare` | `design-compare:design-compare` |
| 8 | `swift-code-reviewer-skill` | `swift-code-reviewer` |
| 8 fallback | `/code-review` | `swift-code-reviewer` или доступный `gsd-code-review` |

## Параллельные фичи

Внутри текущего запроса — `collaboration.spawn_agent`. Отдельные Codex tasks — только по явной просьбе пользователя.

## Preflight-чеклист

- [ ] До Figma-вызовов выполнен read-only аудит Strings / Typography / Colors / Images / Accessibility по `../references/project-ui-conventions.md`; пять строк контракта готовы для переноса в manifest. Для Strings сначала прочитана документация и разрешён контракт из `../references/strings-workflow.md`, затем один compact inventory без catalog dump. Accessibility без явного требования → `skill-fallback: no-add`.
- [ ] Полностью прочитан `../references/figma-mcp-acquisition.md`; transport/read capabilities/optional capabilities/target/write=`disabled` готовы для manifest.
- [ ] Figma URL локально распарсен; `fileKey` и `node-id` известны до пробного реального вызова.
- [ ] Наличие official generic и SwiftUI translator проверено независимо; зарегистрированный `figma-design-to-code` загружен до первого context call и только тогда попадает в `skillNames` (с `resource:` при MCP-resource загрузке), иначе выбран документированный fallback.
- [ ] UI Plan template/validator доступны; self-check проходит: `python3 <skill-root>/scripts/ui_plan.py validate --plan <skill-root>/templates/UI_PLAN.template.json --phase ui --allow-placeholders`.
- [ ] Figma tools отвечают реальным metadata-first вызовом по parent node. Code Connect/motion недоступны → записан `degraded` fallback, а не ложный общий blocker; Figma write-tools не вызваны.
- [ ] xcodebuildmcp `session_show_defaults` отвечает.
- [ ] `FIGMA_ACCESS_TOKEN` доступен (этап 5) — иначе блокер этапа 5.

Отсутствующее без fallback — одним списком, прямым вопросом пользователю.
