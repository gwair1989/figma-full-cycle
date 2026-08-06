# Strings Workflow: documentation-first и с ограниченным контекстом

Прочитать полностью, когда фича затрагивает видимый пользователю copy или когда Strings-строка аудита ещё не разрешена. Цель — соблюдать механизм конкретного проекта и не загружать в контекст целые `*.xcstrings`, `*.strings` или `*.stringsdict`.

## Неподвижные правила

1. Проектная документация определяет механизм Strings. Этот workflow не выбирает самостоятельно формат, catalog/table, bundle, API, стиль ключей, extraction mode, generated symbols, source locale, набор локалей или владельца переводов.
2. Приоритет: применимые project instructions → документация проекта → уже разрешённый Strings-контракт в manifest → однозначный существующий механизм → baseline скилла.
3. Helper `scripts/localization_context.py` только читает и агрегирует. Он локально парсит resource bytes, но наружу отдаёт bounded summary — catalog bytes не попадают в модельный контекст. Helper не изменяет каталоги, не придумывает ключи/переводы и не заменяет build проекта.
4. Полный каталог, полный `git diff` каталога и все переводы не передавать модели или subagent'ам. По умолчанию нужны только счётчики, точечные совпадения и key-level diff.
5. Не мигрировать `.strings` в `.xcstrings`, не создавать второй localization-путь и не включать generated symbols/extraction settings в рамках фичи, если это явно не предписано проектом.

## 1. Сначала разрешить Strings-контракт

До чтения Figma и до inventory найти правила Strings в порядке из `project-ui-conventions.md`: `AGENTS.md`/`CLAUDE.md`, `README*`, `CONTRIBUTING*`, `docs/**`, документация owning target/module/package. Искомые термины: `String Catalog`, `xcstrings`, `Localizable.strings`, `stringsdict`, `localization`, `table`, `bundle`, `LocalizedStringResource`, `String(localized:)`, `NSLocalizedString`, `SWIFT_EMIT_LOC_STRINGS`, `STRING_CATALOG_GENERATE_SYMBOLS`, `generated symbols`, `source language`, `translation`.

Записать в manifest компактный контракт:

- точные источники документации: path + section/symbol;
- разрешённый механизм: `xcstrings-auto`, `xcstrings-manual`, `xcstrings-generated-symbols`, `strings`, `strings+stringsdict` или проектный вариант;
- owning target/module, resource path, catalog/table и bundle;
- разрешённые API и стиль ключей;
- для opaque/generated keys — документированный allocator/naming source; если новый key нельзя однозначно получить, `conflict` до реализации;
- extraction mode и generated-symbol policy;
- source locale, поддерживаемые локали и правила fallback;
- кто создаёт/проверяет переводы и разрешено ли агенту их писать;
- правила comments/placeholders, кто создаёт plural/device variation structure, и validation/build;
- статус сопоставления с baseline скилла.

Если документация отвечает не на всё, проверять только недостающие пункты по build settings, существующим ресурсам и 2–3 репрезентативным call sites. Помечать это `inferred-from-code`, а не выдавать за документированное правило. Если нет ни документированного правила, ни однозначного существующего механизма, поставить `conflict` и спросить до первой новой user-facing строки.

Accessibility copy входит в Strings-контракт только при активном Accessibility-контракте. Baseline Accessibility `no-add` не создаёт labels/hints и соответствующие ключи.

## 2. Один компактный inventory вместо чтения каталогов

После разрешения документации выполнить один inventory из корня или минимального owning scope:

```bash
python3 <skill-root>/scripts/localization_context.py inventory --root <repo-or-owning-scope>
```

По умолчанию команда не печатает ключи и значения. В manifest сохранить только: paths/types, counts, source locale, locales, detected key style, variation/extraction-state counts и parse errors. `--samples` не использовать, если конкретные примеры не нужны для неразрешённого пункта контракта; тогда задать малое число явно.

Inventory подтверждает фактический механизм, но не отменяет документацию. При расхождении документации и ресурсов поставить `conflict` или явно разрешённое `project-specific` решение — не угадывать.

## 3. Один feature copy inventory

На этапе 1 собрать copy всех экранов и состояний один раз. Одна строка таблицы = одна уникальная семантическая единица, а не одно визуальное вхождение. Для каждой единицы хранить:

- `copy_id`, source copy и все usages (`screen/state/control`);
- kind: simple / interpolation / plural / variant;
- параметры и translator context;
- предполагаемые catalog/table только из Strings-контракта;
- найденный existing key/symbol или статус `new`;
- статус `reuse / new / TBD / implemented / verified`.

Дедуплицировать только одинаковый смысл и translator context. Одинаковый текст с разным смыслом может требовать разных ключей; разные Figma-вхождения одного смысла должны переиспользовать одну запись. Опечатку/расхождение copy зафиксировать один раз, не размножать по экранам.

## 4. Один batched lookup

Сделать один lookup по всем уникальным source values и известным ключам. Для больших наборов использовать newline/JSON query file в gitignored runtime, а не много отдельных поисков:

```bash
python3 <skill-root>/scripts/localization_context.py lookup \
  --root <repo-or-owning-scope> \
  --values-file <batched-values-file> \
  --keys-file <batched-keys-file> \
  --source-locale <documented-source-locale>
```

Перед вызовом дедуплицировать query: передавать только непустые файлы и не повторять natural-language строку одновременно как key и value, если проект не разделяет stable key/default value. Lookup по умолчанию возвращает только catalog, key, kind, locales, extraction state и короткий comment. Значения включать только для нужной source/target locale через `--show-values --locale <locale>`. `--contains` использовать лишь для узкого расследования; широкий substring-поиск быстро создаёт шум. Default `--limit 20`; `MATCHES_TRUNCATED` не считается полным gate — сузить owning scope/table или осознанно поднять limit, пока каждая строка feature copy inventory не получит явный результат. Каталог целиком не печатать.

Результат lookup свести в feature copy inventory. Не сохранять сырой вывод или весь catalog в manifest.

## 5. Одна batched-реализация по механизму проекта

После утверждения inventory внести Strings-изменения одним логическим batch, а не по экрану и не с build после каждой строки.

- `xcstrings-auto`: сначала использовать разрешённые localizable API в коде, затем один extraction/project build согласно документации. Этот успешный build одновременно служит stage build; не повторять его без последующих изменений. Не добавлять вручную запись, которую проект/Xcode извлекает из кода.
- `xcstrings-manual` или generated symbols: применять только проектный generator/editor/workflow и naming. Не включать build settings и не изобретать symbol names. После добавления выполнить один generation/build cycle, если это требует проект.
- `Localizable.strings`: менять только разрешённые table/bundle и минимальный набор ожидаемых ключей. Для plural использовать существующий проектный `.stringsdict`-механизм; не мигрировать формат ради фичи.
- Интерполяцию/placeholders/variants задавать согласно контракту; не собирать локализуемые предложения конкатенацией фрагментов.
- Auto-extraction строки с параметром не даёт автоматического разрешения редактировать plural/device variations: создавать их только если Strings-контракт назначает это агенту, иначе включить в translation handoff.
- Не придумывать переводы и не копировать source value во все локали. Добавлять target-locale значения только если документация проекта прямо разрешает агенту это делать и предоставлен проверяемый перевод. Иначе одним batch записать translation owner, handoff artifact/status и допустимость merge с pending translations по правилам проекта.

В контекст worker/subagent передавать только Strings-контракт и его строки feature copy inventory. Каталог целиком не передавать; worker не выбирает новые ключи или таблицы самостоятельно.

## 6. Key-level gate вместо полного diff

После batch-изменения проверить только localization-файлы, затронутые с base SHA этапа, и только ожидаемые feature keys:

```bash
python3 <skill-root>/scripts/localization_context.py diff \
  --root <repo-or-owning-scope> \
  --base <STRINGS_BASE_SHA> \
  --entries-file <expected-path-qualified-entries-file> \
  --strict

python3 <skill-root>/scripts/localization_context.py validate \
  --root <repo-or-owning-scope> \
  --changed-from <STRINGS_BASE_SHA> \
  --xcode
```

Expected entries — точный набор физически затронутых пар `repo-relative-path::key`, по одной строке в newline/JSON array; reuse без изменения туда не включать. Path записывать относительно git root ровно как в `FILE path=`. Это сохраняет связь key→catalog/locale и не позволяет правильному key попасть в чужой ресурс. Для единственного файла допустима короткая форма `--keys-file` + `--paths-file`, но для нескольких paths path-qualified entries обязательны. Новый localization-файл по умолчанию запрещён и требует документированного разрешения плюс явный `--expected-added-path <repo-relative-path>`; удаление не разрешается. Если ожидается ноль key changes, использовать отдельный `--expect-no-key-changes`, не смешивая его с expectations.

`diff --strict` блокирует removals, missing/unexpected path-qualified entries, незаявленный file lifecycle, translator-comment removal, raw/order/format churn и catalog-level metadata edits. `validate` проверяет parse/duplicate keys, базовую `.stringsdict` schema, legacy plist syntax и, с `--xcode`, запускает доступный `xcstringstool compile --dry-run` для изменённых `.xcstrings`. Один реальный project build и проектные localization tests/lint выполнить в порядке, требуемом механизмом: auto-extraction build идёт до diff и переиспользуется как gate evidence; manual resources обычно валидируются до build. Не запускать второй build, если после успешного extraction/project build ничего не менялось. Project build остаётся источником истины для placeholder/value-type и project-specific variant rules. Полный raw diff открывать только для конкретной ошибки и узкого key/file fragment.

Gate завершён, когда:

- затронуты только expected feature keys и разрешённые ресурсы;
- auto-extraction не затронул чужие stale keys; их нельзя молча добавлять в expected allowlist;
- нет удалений, неожиданных metadata edits, parse/duplicate/format ошибок;
- generated extraction/symbol state соответствует документированному механизму;
- build/tests проходят;
- feature copy inventory помечен `verified`, а evidence содержит только краткие итоги команд.

Если translation handoff ещё pending, техническое `verified` source-ресурса не означает готовность переводов. Этап 6 использует только разрешённые документацией target locales, sanctioned pseudolocale/fixtures или фиксирует ожидающий translation gate/waiver; агент не генерирует подменные переводы ради визуальной проверки.

## 7. Resume и stale без повторной оплаты

В manifest хранить `STRINGS_BASE_SHA`, paths/sections документации, compact inventory summary и feature copy inventory. При resume:

1. Если документация Strings изменилась — заново разрешить только Strings-контракт.
2. Если изменились catalogs/build settings/mechanism — повторить compact inventory и один lookup только по feature keys/values.
3. Если они не менялись — использовать записанный контракт и inventory; не сканировать/читать каталоги повторно.
4. После loop-back UI обновить только затронутые copy rows и снова выполнить один batched lookup/diff.

## Запрещённые дорогие паттерны

- `cat`/полное чтение `.xcstrings`, всех `.strings` или полного catalog diff в модель;
- повторный repo-wide search, lookup или build для каждой строки/экрана;
- передача catalog blob нескольким subagent'ам;
- ручное редактирование auto-extracted записи до изменения кода;
- массовая перезапись JSON/plist, сортировка всего catalog или «cleanup» чужих keys;
- генерация переводов без разрешённой проектной политики.

## Apple references

- [Localizing and varying text with a string catalog](https://developer.apple.com/documentation/xcode/localizing-and-varying-text-with-a-string-catalog)
- [Preparing your app's text for translation](https://developer.apple.com/documentation/xcode/preparing-your-apps-text-for-translation)
- [Using generated localizable symbols in your code](https://developer.apple.com/documentation/xcode/using-generated-localizable-symbols-in-your-code)
- [Localizing strings that contain plurals](https://developer.apple.com/documentation/xcode/localizing-strings-that-contain-plurals)
