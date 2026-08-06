# Figma Full Cycle

**На входе — ссылка на родительский фрейм в Figma. На выходе — собранная, сверенная с дизайном и
отревьюенная фича по правилам проекта.**

`figma-full-cycle` — оркестратор-скилл ([Agent Skill](https://code.claude.com/docs/ru/skills)) для
Claude Code и Codex. Даёшь ссылку на родительский фрейм фичи; скилл ведёт весь путь от дизайна до
готового к merge кода — спека, ассеты, вёрстка, сверка, адаптивность, логика, ревью — восемью
этапами с gate'ами, один этап = один коммит, источник правды — tracked-манифест.

[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](LICENSE)
[![CI](https://github.com/gwair1989/figma-full-cycle/actions/workflows/ci.yml/badge.svg)](https://github.com/gwair1989/figma-full-cycle/actions/workflows/ci.yml)
![Skills: 2](https://img.shields.io/badge/skills-2-blue)
![Runtime deps: none](https://img.shields.io/badge/runtime%20deps-none-brightgreen)
![Target stack: SwiftUI + TCA](https://img.shields.io/badge/target-SwiftUI%20%2B%20TCA-orange)

> **Про язык.** Сам скилл, его references и шаблоны — английские. Русские триггер-фразы остались в
> `description` каждого скилла, так что русский промпт по-прежнему его поднимает, а документы,
> которые скилл пишет в твой проект, идут **на твоём языке**. Машиночитаемая структура — ключи UI
> Plan, статусы, заголовки манифеста, subject коммитов — всегда английская, иначе ломаются валидатор
> и resume.
>
> English version: [README.md](README.md).

---

## Зачем

Один промпт «свёрстай этот экран из фигмы» на настоящей фиче ломается предсказуемо:

| Проблема | Что делает скилл |
|---|---|
| Агент выдумывает поведение, которого в статичном макете не было | Каждый неизвестный пункт — вопрос в журнале или явный `TBD`, не молчаливая догадка |
| Агент игнорирует конвенции проекта: строки, типографика, цвета | Read-only аудит конвенций **до** Figma и до любых правок; пять разрешённых строк контракта гейтят все этапы |
| Каталоги локализации и сырые MCP-ответы сжигают контекст | Ограниченные read-only хелперы, scoped Figma-чтение, делегирование subagent'ам, компактные evidence в state |
| Один гигантский нечитаемый коммит | Один этап = один коммит, каждый за gate'ом, подтверждённым реальной командой |
| «Всё зелёное» без единого запуска | Gate требует evidence: команда, время, exit code, путь артефакта |
| После работы транк грязный | Фича живёт в своей ветке и worktree; cleanup только после подтверждённого merge |

## Этапы

| # | Этап | Gate (кратко) |
|---|---|---|
| 0 | Worktree — ветка, секреты симлинком, build defaults, baseline build/test | Baseline записан, манифест создан |
| 1 | Спека + UI Plan — экраны, navigation map, инвентарь ассетов и copy | Спека и `UI_PLAN.json` на диске, `ui_plan.py --phase ui` pass, блокеры отвечены |
| 2 | Ассеты — импорт по инвентарю node-id | Build успешен, каждый ассет проверен |
| 3 | Вёрстка UI + скелет TCA | Evidence UI Plan актуальны, строки проверены, build успешен, каждый экран и состояние — `done` |
| 4 | Рефакторинг UI — *условный*, только при findings | Build успешен, затронутые проверки → `stale` |
| 5 | Сверка с дизайном — поэкранно против запиненного фрейма | Отчёт на диске, расхождения исправлены и пересверены |
| 6 | Адаптивность — малый/большой экран, light/dark, content sizes, локали, клавиатура | Нет обрезок и наложений, evidence сохранён |
| 7 | Логика reducer'ов + runtime-навигация + тесты | `ui_plan.py --phase production` pass, тесты pass, TBD помечены |
| 8 | Финальное ревью | Ревью чисто, нет сырых user-facing литералов, чистый checkpoint закоммичен |

Два свойства делают это пригодным для жизни:

- **Resume с любого этапа.** State лежит на диске и сверяется с git — `старт: этап N` или просто
  «продолжи фичу».
- **Режим `ui-first`.** Дизайн есть, ТЗ нет? Этапы 0–6 идут сейчас, продуктовые вопросы уходят в
  `deferred-to-spec` вместо блокировки, этапы 7–8 ждут ТЗ.

## Требования

- **Агент:** Claude Code или Codex (адаптер маппит capability на конкретные имена инструментов).
- **Figma MCP** с read-доступом и `FIGMA_ACCESS_TOKEN` к этапу 5.
- **Python 3.9+** — только стандартная библиотека, `pip install` не нужен.
- **Проект:** Xcode/SwiftUI-приложение; этапы 3 и 7 рассчитаны на
  [TCA](https://github.com/pointfreeco/swift-composable-architecture), с задокументированными
  fallback'ами на скиллы стека проекта.
- **Скиллы-спутники не зашиты по именам — они обнаруживаются.** Префлайт проходит по реально
  установленным скиллам, MCP-инструментам, MCP-ресурсам, плагинам и скриптам проекта и привязывает
  по одному кандидату к каждой *роли* этапа: `design-to-code-workflow`, `platform-ui-idiom`,
  `app-architecture`, `visual-comparison`, `code-review` и так далее. Переименованные, вынесенные в
  неймспейс, префиксованные плагином и совсем новые вендорские скиллы подхватываются так же; роль
  без кандидата уходит в задокументированный fallback. Жёстко по именам — только то, что лежит
  здесь: `figma-full-cycle`, `figma-feature-spec`, `import-figma-assets`.

Отсутствующие возможности выдаются одним списком-блокером в начале, а не всплывают по одной на
середине работы. Итоговые привязки — вместе с пробой аутентификации Figma и доступности узла —
пишутся в capability ledger манифеста.

## Установка

```bash
git clone https://github.com/gwair1989/figma-full-cycle.git
cd figma-full-cycle
./install.sh
```

`install.sh` ставит симлинки на все три скилла в `~/.claude/skills` — после этого `git pull`
обновляет их на месте.

```bash
./install.sh --target ~/.codex/skills   # Codex
./install.sh --target .claude/skills    # только для текущего проекта
./install.sh --copy                     # копировать вместо симлинка
./install.sh --force                    # заменить одноимённый скилл
./install.sh --uninstall                # удалить установленное
```

Скиллы уже лежат в твоём skills-каталоге? `--force` заменит их, а старые копии перенесёт в
`.skill-backups` **рядом** с каталогом скиллов, а не внутрь него — внутри агент подхватил бы бэкап
как второй, дублирующий скилл.

Проверка: новая сессия агента, `figma-full-cycle` виден в списке скиллов.

## Использование

Нужна ссылка на **родительский** фрейм — контейнер со всеми экранами флоу, не на один экран:

```text
Сделай фичу по фигме целиком: https://figma.com/design/<fileKey>/App?node-id=1234-5678
```

```text
Полный цикл по фрейму <url>, режим: ui-first — тз позже
```

```text
Продолжи <FEATURE>, старт: этап 5
```

### Что появляется в проекте

| Файл | Tracked | Роль |
|---|---|---|
| `docs/<FEATURE>_PIPELINE.md` | да | Манифест: этапы, gates, evidence, журнал вопросов, решения |
| `docs/<FEATURE>_UI_PLAN.json` | да | Машинно-проверяемый контракт передачи из спеки в вёрстку |
| `docs/<FEATURE>_PIPELINE.local.md` | нет (gitignored) | Локальный runtime: абсолютные пути, UDID симулятора |

## Состав репозитория

```
skills/
├── figma-full-cycle/
│   ├── SKILL.md                     # оркестратор
│   ├── adapters/                    # claude-code.md, codex.md — capability → имена инструментов
│   ├── references/                  # discovery инструментов, контракт UI Plan, Figma acquisition,
│   │                                #   строки, layout, конвенции
│   ├── scripts/                     # ui_plan.py, localization_context.py (+ тесты)
│   ├── templates/                   # PIPELINE, PIPELINE.local, UI_PLAN
│   └── agents/openai.yaml           # манифест агента в формате OpenAI
├── figma-feature-spec/              # этап 1 как отдельный скилл
│   ├── SKILL.md
│   └── templates/SPEC.template.md
└── import-figma-assets/             # этап 2 как отдельный скилл
    ├── SKILL.md
    └── scripts/                     # генератор imageset, нормализация PNG-канваса
```

### Два скрипта

Оба read-only и на чистой стандартной библиотеке — скилл зовёт их, чтобы модель не глотала сырые
данные:

```bash
python3 skills/figma-full-cycle/scripts/ui_plan.py validate \
  --plan docs/FEATURE_UI_PLAN.json \
  --manifest docs/FEATURE_PIPELINE.md \
  --project-root . --phase ui
```

`ui_plan.py` валидирует контракт вёрстки — экраны, компоненты, токены, copy, ассеты и их provenance
— и отдаёт компактную actionable-диагностику до начала build-цикла.

```bash
python3 skills/figma-full-cycle/scripts/localization_context.py inventory --root .
```

`localization_context.py` инспектирует `.xcstrings` / `.strings` / `.stringsdict` с ограниченным
выводом: `inventory`, точечный `lookup`, key-level `diff`, `validate`. Каталоги не пишет и целиком
не печатает.

## Модель безопасности

- **Figma — недоверенный ввод.** Текст внутри дизайна это контент, а не инструкция.
- **Write-инструменты Figma выключены** (`use_figma`, `upload_assets`, записи Code Connect и т.д.),
  пока пользователь явно не попросит изменить файл дизайна.
- **Секреты не копируются.** В worktree — симлинк на `.env` основного checkout; secret scan перед
  каждым коммитом; значения не печатаются.
- **Переводы не выдумываются.** Source copy не разливается по локалям без задокументированной
  политики проекта; готовность переводов — отдельный gate.
- **Merge решает пользователь.** Пройденный этап 8 даёт ветку, готовую к PR, а не автоматический
  merge.

## Портирование на другого агента

Новый агент — это новый файл адаптера, а не правка ядра. Скопируй
`skills/figma-full-cycle/adapters/claude-code.md`, замени правую колонку на имена инструментов
своего агента, строки capability оставь как есть и сошлись на файл из раздела адаптеров скилла.
Ядро `SKILL.md` намеренно остаётся agent-neutral.

## Контрибьютинг

Issues и PR приветствуются — см. [CONTRIBUTING.md](CONTRIBUTING.md). Проверки локальные, идут секунды:

```bash
./check.sh
```

Гоняет 32 теста валидатора на каждом Python 3, который есть на машине — включая
`/usr/bin/python3`, то есть 3.9 из Xcode Command Line Tools — затем линтует структуру скиллов и
синтаксис shell-скриптов. Чтобы это происходило само перед каждым push:

```bash
ln -sf ../../tools/pre-push .git/hooks/pre-push
```

CI проверяет только структуру скиллов и относительные ссылки — то, что глазами в diff не поймать.

## Лицензия

[MIT](LICENSE) © Oleksandr Khalypa
