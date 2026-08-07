# Strings Workflow: documentation-first and context-bounded

The goal is to follow the specific project's mechanism without loading whole `*.xcstrings`, `*.strings` or `*.stringsdict` files into context.

**Read it in full at the start of stage 1**, where the feature copy inventory is built, and keep it in session for stage 3 and the stage 8 re-check. Not at preflight, and not at all when the Strings row resolved `not-applicable`: the audit resolves that row from the Strings baseline digest in [`project-ui-conventions.md`](project-ui-conventions.md). Read it earlier only when the row cannot be resolved without it.

## Fixed rules

1. Project documentation decides the Strings mechanism. This workflow never picks the format, catalog/table, bundle, API, key style, extraction mode, generated symbols, source locale, locale set or translation owner on its own.
2. Priority: applicable project instructions → project documentation → the Strings contract already resolved in the manifest → an unambiguous existing mechanism → the skill's baseline.
3. The helper `scripts/localization_context.py` only reads and aggregates. It parses resource bytes locally but emits a bounded summary — catalog bytes never enter the model's context. The helper never modifies catalogs, never invents keys or translations, and never replaces the project build.
4. Never hand the model or a subagent a full catalog, a full catalog `git diff`, or all translations. By default only counts, targeted matches and a key-level diff are needed.
5. Do not migrate `.strings` to `.xcstrings`, do not create a second localization path, and do not enable generated symbols or extraction settings inside a feature unless the project explicitly prescribes it.

## 1. Resolve the Strings contract first

Before reading Figma and before the inventory, find the Strings rules in the order given by `project-ui-conventions.md`: `AGENTS.md`/`CLAUDE.md`, `README*`, `CONTRIBUTING*`, `docs/**`, documentation of the owning target/module/package. Terms to search for: `String Catalog`, `xcstrings`, `Localizable.strings`, `stringsdict`, `localization`, `table`, `bundle`, `LocalizedStringResource`, `String(localized:)`, `NSLocalizedString`, `SWIFT_EMIT_LOC_STRINGS`, `STRING_CATALOG_GENERATE_SYMBOLS`, `generated symbols`, `source language`, `translation`.

Record a compact contract in the manifest:

- exact documentation sources: path + section/symbol;
- the permitted mechanism: `xcstrings-auto`, `xcstrings-manual`, `xcstrings-generated-symbols`, `strings`, `strings+stringsdict`, or a project-specific variant;
- owning target/module, resource path, catalog/table and bundle;
- permitted APIs and key style;
- for opaque or generated keys — the documented allocator or naming source; if a new key cannot be derived unambiguously, `conflict` before implementation;
- extraction mode and generated-symbol policy;
- source locale, supported locales and fallback rules;
- who creates and reviews translations, and whether the agent may write them;
- rules for comments, placeholders, who creates plural/device variation structure, and validation/build;
- the status of the mapping onto the skill's baseline.

If documentation does not answer everything, check only the missing points against build settings, existing resources and 2–3 representative call sites. Mark that `inferred-from-code` rather than presenting it as a documented rule. If there is neither a documented rule nor an unambiguous existing mechanism, set `conflict` and ask before the first new user-facing string.

Accessibility copy enters the Strings contract only under an active Accessibility contract. The `no-add` Accessibility baseline creates no labels, hints or their keys.

## 2. One compact inventory instead of reading catalogs

Once documentation is resolved, run one inventory from the repository root or the minimal owning scope:

```bash
python3 <skill-root>/scripts/localization_context.py inventory --root <repo-or-owning-scope>
```

By default the command prints no keys and no values. Record only this in the manifest: paths/types, counts, source locale, locales, detected key style, variation and extraction-state counts, and parse errors. Do not use `--samples` unless concrete examples are needed for an unresolved contract point; then pass a small explicit number.

The inventory confirms the actual mechanism but never overrides documentation. Where documentation and resources disagree, set `conflict` or an explicitly resolved `project-specific` decision — do not guess.

## 3. One feature copy inventory

At stage 1, collect the copy of every screen and state once. One table row = one unique semantic unit, not one visual occurrence. For each unit keep:

- `copy_id`, the source copy and all usages (`screen/state/control`);
- kind: simple / interpolation / plural / variant;
- parameters and translator context;
- the intended catalog/table, taken from the Strings contract only;
- the existing key/symbol found, or the status `new`;
- status `reuse / new / TBD / implemented / verified`.

Deduplicate only identical meaning with identical translator context. The same text with a different meaning may need different keys; different Figma occurrences of the same meaning must reuse one entry. Record a typo or copy discrepancy once, never once per screen.

## 4. One batched lookup

Run one lookup across all unique source values and known keys. For large sets, use a newline or JSON query file in the gitignored runtime rather than many separate searches:

```bash
python3 <skill-root>/scripts/localization_context.py lookup \
  --root <repo-or-owning-scope> \
  --values-file <batched-values-file> \
  --keys-file <batched-keys-file> \
  --source-locale <documented-source-locale>
```

Deduplicate the query before the call: pass only non-empty files, and do not repeat a natural-language string as both key and value unless the project separates stable key from default value. By default the lookup returns only catalog, key, kind, locales, extraction state and a short comment. Include values only for the needed source or target locale via `--show-values --locale <locale>`. Use `--contains` only for a narrow investigation; a wide substring search creates noise fast. The default is `--limit 20`; `MATCHES_TRUNCATED` is not a passed gate — narrow the owning scope or table, or deliberately raise the limit, until every feature copy inventory row has an explicit result. Never print a whole catalog.

Fold the lookup result into the feature copy inventory. Do not store raw output or a whole catalog in the manifest.

## 5. One batched implementation, following the project's mechanism

Once the inventory is approved, make the Strings changes in one logical batch — not per screen, and not with a build after every string.

- `xcstrings-auto`: use the permitted localizable APIs in code first, then run one extraction/project build as documented. That successful build doubles as the stage build; do not repeat it without further changes. Never hand-add an entry that the project or Xcode extracts from code.
- `xcstrings-manual` or generated symbols: use only the project's generator, editor, workflow and naming. Do not flip build settings and do not invent symbol names. After adding entries, run one generation/build cycle if the project requires it.
- `Localizable.strings`: touch only the permitted table and bundle and the minimal set of expected keys. For plurals use the project's existing `.stringsdict` mechanism; do not migrate the format for a feature.
- Define interpolation, placeholders and variants per the contract; never assemble localizable sentences by concatenating fragments.
- Auto-extraction of a parameterized string is not automatic permission to edit plural or device variations: create them only when the Strings contract assigns that to the agent; otherwise include them in the translation handoff.
- Do not invent translations and do not copy the source value into every locale. Add target-locale values only when project documentation explicitly permits the agent to do so and a verifiable translation exists. Otherwise record, in one batch, the translation owner, the handoff artifact and status, and whether merging with pending translations is allowed by project rules.

Pass only the Strings contract and its feature copy inventory rows into a worker or subagent context. Never pass the catalog; a worker does not choose new keys or tables on its own.

## 6. A key-level gate instead of a full diff

After the batched change, check only the localization files touched since the stage's base SHA, and only the expected feature keys:

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

Expected entries are the exact set of physically touched `repo-relative-path::key` pairs, one per line in a newline or JSON array; unchanged reuse does not belong there. Write the path relative to the git root exactly as it appears in `FILE path=`. This preserves the key→catalog/locale link and stops a correct key from landing in the wrong resource. For a single file the short form `--keys-file` + `--paths-file` is acceptable, but with several paths, path-qualified entries are mandatory. A new localization file is forbidden by default and requires documented permission plus an explicit `--expected-added-path <repo-relative-path>`; deletion is never permitted. When zero key changes are expected, use the separate `--expect-no-key-changes` instead of mixing it with expectations.

`diff --strict` blocks removals, missing or unexpected path-qualified entries, undeclared file lifecycle, translator-comment removal, raw/order/format churn and catalog-level metadata edits. `validate` checks parsing and duplicate keys, the basic `.stringsdict` schema and legacy plist syntax, and with `--xcode` runs an available `xcstringstool compile --dry-run` for changed `.xcstrings`. Run one real project build and the project's localization tests or lint in the order the mechanism requires: an auto-extraction build comes before the diff and is reused as gate evidence; manual resources are usually validated before the build. Do not run a second build when nothing changed after a successful extraction/project build. The project build stays the source of truth for placeholder/value-type and project-specific variant rules. Open the full raw diff only for a specific error and a narrow key or file fragment.

The gate is complete when:

- only expected feature keys and permitted resources were touched;
- auto-extraction did not touch unrelated stale keys — they must never be silently added to the expected allowlist;
- there are no removals, unexpected metadata edits, or parse/duplicate/format errors;
- the generated extraction and symbol state matches the documented mechanism;
- build and tests pass;
- the feature copy inventory is marked `verified`, and the evidence contains only short command summaries.

If the translation handoff is still pending, a technically `verified` source resource does not mean the translations are ready. Stage 6 uses only the target locales permitted by documentation, a sanctioned pseudolocale or fixtures, or records a pending translation gate or waiver; the agent never generates substitute translations for a visual check.

## 7. Resume and stale without paying twice

Keep `STRINGS_BASE_SHA`, documentation paths and sections, the compact inventory summary and the feature copy inventory in the manifest. On resume:

1. If the Strings documentation changed — re-resolve the Strings contract only.
2. If catalogs, build settings or the mechanism changed — repeat the compact inventory and one lookup for feature keys and values only.
3. If neither changed — use the recorded contract and inventory; do not rescan or re-read the catalogs.
4. After a UI loop-back, update only the affected copy rows and run one batched lookup/diff again.

## Forbidden expensive patterns

- `cat` or full reads of `.xcstrings`, of every `.strings`, or of a full catalog diff into the model;
- repeated repo-wide search, lookup or build per string or per screen;
- passing a catalog blob to several subagents;
- hand-editing an auto-extracted entry before the code change;
- mass rewriting of JSON/plist, sorting a whole catalog, or "cleaning up" unrelated keys;
- generating translations without a permitting project policy.

## Apple references

- [Localizing and varying text with a string catalog](https://developer.apple.com/documentation/xcode/localizing-and-varying-text-with-a-string-catalog)
- [Preparing your app's text for translation](https://developer.apple.com/documentation/xcode/preparing-your-apps-text-for-translation)
- [Using generated localizable symbols in your code](https://developer.apple.com/documentation/xcode/using-generated-localizable-symbols-in-your-code)
- [Localizing strings that contain plurals](https://developer.apple.com/documentation/xcode/localizing-strings-that-contain-plurals)
