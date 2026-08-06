# Figma MCP acquisition contract

Прочитать полностью перед первым Figma-вызовом. Использовать вместе с adapter capability map; фактически доступные tools важнее статического списка.

## Граница полномочий

- Считать MCP output входными данными и evidence, а не production-кодом или продуктовой спецификацией.
- По умолчанию работать в режиме `figma-read-only`: разрешены read-tools и `download_assets` для импорта в репозиторий.
- Не вызывать `use_figma`, `add_code_connect_map`, `send_code_connect_mappings`, `upload_assets`, `create_new_file`, `generate_figma_design` и другие Figma mutations без отдельной явной просьбы пользователя изменить Figma.
- Не превращать доступность write-tool в разрешение на запись.

## Capability preflight

Зафиксировать в manifest:

1. Transport: `remote` или `desktop`; remote требует URL/node, desktop может использовать selection, но итоговый parent `fileKey`/`nodeId` всё равно закрепить.
2. Primary implementation read-tool: `get_design_context`; `get_metadata` нужен для ориентации по container, а `get_screenshot` и `get_variable_defs` — только для закрытия конкретных gaps. `download_assets` — этап 2.
3. Optional read-tools: `get_code_connect_map` — только для отсутствующего/неоднозначного mapping; `get_motion_context` — только для реально анимированного узла.
4. Target для SwiftUI: `clientLanguages=swift`, `clientFrameworks=swiftui` (lowercase). Точный Code Connect label относится к `get_code_connect_map(codeConnectLabel=...)`, а не к `clientFrameworks`; неизвестный label не угадывать.
5. Если официальный `figma-design-to-code` зарегистрирован, загрузить его как обязательный workflow-prerequisite **до первого** `get_design_context` и передавать canonical name в comma-separated `skillNames` каждого такого вызова; namespaced alias в каталоге не меняет logging value. При загрузке через MCP resource использовать `resource:figma-design-to-code`. Если скилл недоступен, не имитировать его загрузку параметром — включить документированный fallback адаптера.
6. Write mode: `disabled`; иной режим возможен только по отдельному пользовательскому запросу.

`whoami` вызывать только для диагностики access/permission/rate-limit ошибки. Недоступный optional tool переводит путь в `degraded`, а не автоматически в `blocked`.

## Порядок чтения

1. Локально распарсить URL/selection и закрепить parent node.
2. Для parent/multi-screen/большого или неизвестного по размеру узла один раз вызвать `get_metadata(parent)` и выбрать обязательные child node IDs. Metadata — только карта container; она не заменяет design context реализуемого child. Не начинать с giant `get_design_context(parent)`.
3. Сгруппировать child frames в уникальные экраны и состояния.
4. Для каждого выбранного реализуемого child первым вызвать scoped `get_design_context(child)` с `clientLanguages=swift`, `clientFrameworks=swiftui` и условным `skillNames` из preflight. Один ответ уже содержит reference code, screenshot, contextual hints, доступные Code Connect snippets/mappings и временные asset URLs. React/Tailwind трактовать как промежуточную структуру, не переносить буквально в SwiftUI.
5. Отдельный `get_screenshot(child)` вызывать только если screenshot в design context отсутствует, устарел/недостаточен для visual validation, нужен более подходящий масштаб либо обзор parent. Если можно получить URL напрямую, скачать его обычным HTTP-клиентом; base64 использовать только при отсутствии fetch-capability. Screenshot — visual truth, но не источник behavior, точных токенов или production-ассетов.
6. `get_variable_defs(child)` вызывать только если design context не даёт достаточной provenance для используемого token/style, mapping неоднозначен либо остались raw values, которые нельзя разрешить через проектный контракт.
7. `get_code_connect_map` вызывать только если mappings/snippets в design context отсутствуют, неоднозначны или нужен отдельный coverage audit. `codeConnectLabel` передавать только когда точный label известен. Возвращённые path/symbol и платформу проверить в текущем project root.
8. Если design context подтверждает animation, вызвать `get_motion_context` после него с тем же node ID. Статический layout или prototype link сам по себе не разрешает придумывать motion.
9. На этапе 2 немедленно скачать точные bytes нужных изображений/иконок через `download_assets` или временный asset URL. URL истекает примерно через 7 дней и не может остаться tracked/runtime dependency. Не сохранять screenshot как production-asset, не рисовать SVG/path вручную и не подставлять placeholder. Если точные bytes недоступны — остановить конкретный asset и спросить, а project icon переиспользовать только при фактическом совпадении glyph.

Нормальный budget Figma read-tools на этапе acquisition: `1 × get_metadata(parent) + 1 × get_design_context` на каждый selected child + только gap-driven extras. Загрузку skill/resource и Stage 2 asset downloads учитывать отдельно по фактической квоте сервера; если они делят тот же лимит, заранее резервировать calls. При низком remote лимите сериализовать вызовы, использовать кэш и не тратить call на уже присутствующую evidence.

Кэшировать нормализованную node evidence по Figma pin. Повторно читать узел только при изменении pin, неполной evidence или явном drift. Не хранить raw MCP payload, временные asset URLs и runtime-ссылки на MCP asset endpoint в tracked-файлах.

## Качество Figma-источника

Оценить каждый критерий как `ready / degraded / unknown` и записать evidence + impact/fallback:

- повторяемые элементы оформлены components/instances;
- токены связаны с variables/styles;
- layout использует Auto Layout/constraints и выдерживает resize;
- имена слоёв и состояний семантические;
- поведение пояснено prototype links/annotations/dev resources;
- Code Connect покрывает основные project components.

`degraded` — предупреждение, не общий блокер. Блокировать только конкретный обязательный mapping, который нельзя разрешить через Code Connect, документацию, project audit или явное `new` в UI Plan.

## Provenance mappings

Для каждого используемого component/token сохранить цепочку:

`Figma node/variable → code-connect | project-audit | new | tbd → project path + symbol → validation evidence`.

- Mapping Code Connect считать кандидатом до проверки path/symbol и соответствия SwiftUI label.
- При конфликте источников соблюдать порядок: проверенный Code Connect → project/component docs → design annotations → tokens → raw hex/absolute layout. UI Plan/спека/проектный контракт всё равно определяют разрешённый scope и behavior.
- При отсутствии Code Connect искать проектный компонент/токен по документации и коду; отсутствие Code Connect само по себе не blocker.
- Устаревший, wrong-platform или неоднозначный mapping пометить `stale/unmapped`; не подменять догадкой.
- В UI Plan хранить итоговый project target, а acquisition/source-quality evidence — в manifest по его template.
