# <FEATURE> — Pipeline manifest

> Источник правды полного цикла. Пишет только главный поток скилла `figma-full-cycle`.
> pipeline_schema_version: 7
> run_id: <RUN_ID> <!-- дата+slug; новый при свежем старте, сохраняется при resume -->
> Figma: <FIGMA_URL>
> Figma pin: fileKey=<KEY> node=<NODE> version=<VERSION_OR_HASH> checked_at=<TS>
> Base: <BASE_BRANCH> @ <BASE_SHA>
> Ветка: feature/<FEATURE>
> Спека: docs/<FEATURE>_SPEC.md
> UI Plan: docs/<FEATURE>_UI_PLAN.json schema=1 sha256=<SHA256> validated_at=<TS> phase=<ui|production> status=<todo|valid|stale>
> Режим: <full | ui-first (стоп перед логикой, ждёт ТЗ)>
> Готовность: <production-ready | prototype/UI-only (выбор пользователя) | TBD>
> Runtime (gitignored, не в PR): docs/<FEATURE>_PIPELINE.local.md

## Контракт UI-конвенций проекта (preflight)

> Read-only аудит выполнен до Figma и worktree; сюда перенесён сразу после создания manifest.
> Проверено: base=<BASE_SHA> checked_at=<TS>. При resume перепроверить изменившиеся источники.

| Область | Источники проекта (path + section/symbol) | Правило проекта | Baseline скилла | Итоговое решение | Статус |
|---------|-------------------------------------------|-----------------|------------------|------------------|--------|
| Strings | | | `references/project-ui-conventions.md#strings-baseline` | | `todo` |
| Typography | | | `references/project-ui-conventions.md#typography-baseline` | | `todo` |
| Colors | | | `references/project-ui-conventions.md#colors-baseline` | | `todo` |
| Images | | | `import-figma-assets` + `references/project-ui-conventions.md#images-baseline` | | `todo` |
| Accessibility | | | `references/project-ui-conventions.md#accessibility-baseline` | `no-add`, если нет явного требования документации/пользователя | `todo` |

Статусы: `matched / project-specific / skill-fallback / inferred-from-code / conflict / not-applicable`. Этапы 1–8 не стартуют при `todo` или затрагивающем этап открытом `conflict`. Для Accessibility отсутствие явного требования → `skill-fallback`, решение `no-add`; `inferred-from-code` не активирует scope.

## Figma MCP acquisition (preflight + этап 1)

> Заполнять по `references/figma-mcp-acquisition.md`. Список фактически доступных tools важнее статического каталога; raw MCP payload и временные asset URLs сюда не копировать.

| Transport / input | Read capabilities | Optional capabilities | Target | Write mode | Pin / normalized cache evidence | Статус |
|-------------------|-------------------|-----------------------|--------|------------|---------------------------------|--------|
| `<remote URL+node / desktop selection→pinned node>` | `<metadata, screenshot, design-context, variable-defs, download-assets>` | `<code-connect / motion / unavailable>` | `language=swift; framework=<EXACT_MAPPING_LABEL / iOS-SwiftUI>` | `disabled` | `<fileKey/node/version + local artifact or none>` | `<ready / degraded / blocked>` |

`degraded` допустим при отсутствии optional capability, если выбран и подтверждён fallback. Любая Figma mutation требует отдельного пользовательского запроса и не включается в обычный stage flow.

### Качество Figma-источника

| Критерий | Evidence | Статус | Impact / fallback |
|----------|----------|--------|-------------------|
| Components / instances | | `<ready / degraded / unknown>` | |
| Variables / styles | | `<ready / degraded / unknown>` | |
| Auto Layout / constraints / resize | | `<ready / degraded / unknown>` | |
| Semantic layer / state names | | `<ready / degraded / unknown>` | |
| Prototype / annotations / dev resources | | `<ready / degraded / unknown>` | |
| Code Connect coverage | | `<ready / degraded / unknown>` | `<project audit при отсутствии>` |

`degraded` не блокирует весь этап. Блокировать только обязательный mapping, который нельзя разрешить через Code Connect, project audit или явное `new` в UI Plan.

### Component / token provenance

> Одна строка на используемый component/token. UI Plan хранит итоговый target; здесь — происхождение и проверка mapping.

| Figma node / variable | Kind | Mapping source | Project target (path + symbol) | Label / mapping version | Validation evidence | Статус |
|-----------------------|------|----------------|--------------------------------|-------------------------|---------------------|--------|
| | `<component / token>` | `<code-connect / project-audit / new / tbd>` | | | | `<verified / unmapped / stale / blocked>` |

Code Connect mapping — кандидат до проверки project path/symbol и SwiftUI label. Его отсутствие само по себе не blocker; `unmapped/stale` требует project audit, явного `new` или `tbd` с соответствующим gate.

## Strings snapshot (preflight; compact)

> Заполнять для затронутого Strings scope после документации проекта и одного read-only inventory. Документация определяет механизм; helper только подтверждает факты. Catalog values/raw output сюда не копировать.

| Поле | Разрешённое значение | Источник / evidence |
|------|----------------------|---------------------|
| Mechanism | `<xcstrings-auto / xcstrings-manual / xcstrings-generated-symbols / strings / strings+stringsdict / project-specific / not-applicable>` | `<doc path + section>` |
| Owner / resources | `<target/module; catalog/table; bundle; paths>` | `<doc or inferred symbol>` |
| API / key style | `<allowed API; natural/opaque convention>` | `<doc or representative call sites>` |
| Extraction / symbols | `<mode/settings; generation workflow>` | `<doc + build setting>` |
| Locales | `<source; supported; fallback>` | `<doc>` |
| Translation policy | `<owner; may agent write translations?; TBD flow>` | `<doc>` |
| Variants / comments | `<placeholders; plural/device variants; translator comments; owner of variation structure>` | `<doc>` |
| Validation | `<project build/tests/lint>` | `<doc>` |
| Compact inventory | `<catalog paths/types/counts/locales/states; no values>` | `localization_context.py inventory`, checked_at=`<TS>` |
| Strings base | `<STRINGS_BASE_SHA>` | `<git>` |

## Feature copy inventory (unique semantics only)

> Одна строка на уникальный смысл/translator context, usages перечислять вместе. Не дублировать одинаковый copy по экранам и не хранить полный catalog. Accessibility copy добавлять только при активном Accessibility-контракте.

| Copy ID | Source copy | Usages (compact screen/state/control refs) | Kind / params / translator context | Resource path / catalog / table / bundle | Resolved key/symbol + allocation/lookup evidence | Translation batch/status | Source status |
|---------|-------------|--------------------------------------------|------------------------------------|------------------------------------------|--------------------------------------------------|--------------------------|---------------|
| | | | `<simple / interpolation / plural / variant>` | | | `<none / H1:pending / H1:verified>` | `todo` |

Source statuses: `todo / reuse / new / TBD / implemented / verified`. Этап 1 закрывается после одного полного (без `MATCHES_TRUNCATED`) batched lookup и разрешения каждого key; этап 3 — после exact path-qualified `repo-path::key` `diff --strict`, `validate`, project build и перевода всех затронутых source-строк в `verified`. Reuse без физического изменения не входит в diff expectations. Translation readiness/merge policy определяется только документацией проекта и не маскируется source status.

### Translation handoff batches (только если требует проект)

| Batch | Copy IDs | Owner | Artifact / evidence | Merge policy / due | Статус |
|-------|----------|-------|---------------------|--------------------|--------|
| H1 | | | | | `<pending / handed-off / verified / waived>` |

## Этапы

| # | Этап | Статус | Commit subject | Заметка |
|---|------|--------|----------------|---------|
| 0 | Worktree + toolchain | `todo` | pipeline(<FEATURE>): stage 0 | |
| 1 | Спека + UI Plan | `todo` | pipeline(<FEATURE>): stage 1 | |
| 2 | Ассеты | `todo` | pipeline(<FEATURE>): stage 2 | |
| 3 | Верстка UI + скелет TCA | `todo` | pipeline(<FEATURE>): stage 3 | |
| 4 | Рефакторинг UI (условный) | `todo` | pipeline(<FEATURE>): stage 4 | `skipped` если нет findings |
| 5 | Сверка с дизайном | `todo` | pipeline(<FEATURE>): stage 5 | |
| 6 | Адаптивность | `todo` | pipeline(<FEATURE>): stage 6 | |
| 7 | Reducer-логика | `todo` | pipeline(<FEATURE>): stage 7 | `waiting_user` (ждёт ТЗ) если ui-first |
| 8 | Финал | `todo` | pipeline(<FEATURE>): stage 8 | |

Статусы: `todo / in_progress / blocked / waiting_user / ready_to_commit / done / stale / skipped / waived`.

Resume: сначала reconcile с git — `HEAD`, dirty/untracked, `git log --grep "pipeline(<FEATURE>)"`. `ready_to_commit` + коммит есть → `done`; коммита нет → закоммитить. Затем первый не-`done`/не-`skipped` этап → первая открытая строка его под-чеклиста. SHA в manifest не хранить — восстанавливать по subject.

Commit subject в таблице — **фактический** из git; один этап = один коммит (склейка ломает resume).

## Gate evidence

| Этап | Команда / тул | Время | Результат (exit/итог) | Artifact |
|------|---------------|-------|------------------------|----------|
| | | | | |

## UI Plan evidence

> Заполнять после каждого успешного `ui_plan.py validate`; `schema` и `sha256` копировать из строки `UI_PLAN_VALID`. Любое изменение Figma pin, resolved project contract или самого UI Plan делает запись `stale` до повторной валидации.

| Artifact | Schema | Figma pin | SHA-256 | Validation command | Phase / result | validated_at |
|----------|--------|-----------|---------|--------------------|----------------|--------------|
| `docs/<FEATURE>_UI_PLAN.json` | `1` | `fileKey=<KEY> node=<NODE> version=<VERSION_OR_HASH>` | `<SHA256>` | `python3 <skill-root>/scripts/ui_plan.py validate --plan docs/<FEATURE>_UI_PLAN.json --manifest docs/<FEATURE>_PIPELINE.md --project-root . --phase <ui|production>` | `<ui|production> / valid` | `<TS>` |

## Под-чеклист: ассеты (этап 2)

| Ассет | node-id | Тип | Статус | Проверка (существует / размер / hash) |
|-------|---------|-----|--------|----------------------------------------|
| | | raster/vector | `todo` | |

## Под-чеклист: экраны (этапы 3 / 5)

| Экран | View | Верстка (3) | Сверка (5) | Figma version при сверке |
|-------|------|-------------|------------|--------------------------|
| | | `todo` | `todo` | |

## Матрица адаптивности (этап 6)

Строка на комбинацию. Набор — из deployment target, спеки, Strings-, Typography- и Accessibility-контрактов: минимальный + большой экран; light/dark; разрешённые content sizes; поддерживаемые locale/направления и длинный copy; orientations если поддержаны; клавиатура/safe-area. AX/VoiceOver/Reduce Motion/increased contrast и другие accessibility-only строки добавлять только при явно активированном Accessibility scope; baseline `no-add` их не создаёт.

| Экран | Устройство | Appearance | Content size | Locale / direction | Orientation | Статус | Evidence |
|-------|------------|------------|--------------|--------------------|-------------|--------|----------|
| | | | | | | `todo` | |

## Журнал вопросов

| # | Вопрос | Этап | Блокер | Статус | Ответ / источник |
|---|--------|------|--------|--------|------------------|
| 1 | | | нет | open | |

Статусы: `open` / `answered` / `resolved-from-docs` (указать где нашли: спека/README/AGENTS.md/код) / `deferred-to-spec` (ui-first: ждёт ТЗ, при resume сверить с ним).

## Решения

<!-- Принятые решения, чтобы не переспрашивать. Формат: дата — решение — источник. -->

## Сверка с дизайном (этап 5)

| Экран | Отчёт | ❌ → фикс | Статус |
|-------|-------|-----------|--------|
| | design-compare-reports/<FEATURE>/... | | |

## TBD / заглушки (этап 7)

| Что | Причина | merge-blocking | Waiver (owner / issue / срок) | Статус |
|-----|---------|----------------|-------------------------------|--------|
| | | | | |

`production-ready` невозможен при открытом merge-blocking TBD без waiver.

## Провалы gate (loop-back)

> Полный stdout/stderr хранить отдельным локальным артефактом; сюда переносить компактную диагностическую запись. После третьего неуспешного repair-loop остановиться и запросить решение пользователя.

| Failure ID | Этап / item | Попытка | Compact diagnostic (path:line/symbol; actual → expected) | Raw log artifact | Изменение / гипотеза | Результат / next action |
|------------|--------------|---------|----------------------------------------------------------|------------------|----------------------|--------------------------|
| | | `1/3` | | | | |
