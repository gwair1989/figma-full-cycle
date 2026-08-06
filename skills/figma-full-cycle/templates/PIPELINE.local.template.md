# <FEATURE> — runtime state (gitignored, не в PR)

- Worktree: <ABS_PATH>
- Simulator UDID: <UDID>
- Project/workspace: <PATH>
- Scheme / configuration: <SCHEME> / <CONFIG>
- DerivedData: <PATH>
- Baseline build/test до изменений: <результат; известные исходные падения>
- Strings owning scope: <ABS_PATH_OR_NONE>
- Strings batched query / expected path::key entries files: <GITIGNORED_PATHS_OR_NONE>
- UI Plan transient context / validator logs: <GITIGNORED_PATHS_OR_NONE>
- Figma normalized node-evidence cache: <GITIGNORED_PATH_OR_NONE>
- Figma MCP transient logs/download metadata: <GITIGNORED_PATHS_OR_NONE; NO_TEMP_URLS_IN_TRACKED_FILES>
- Локальные ключи: только имена (значения не записывать)

## Локальные метрики цикла

> Не переносить в tracked manifest. Заполнять по фактам выполнения; `n/a`, если среда не даёт метрику.

| Этап | Started | Finished | Duration | First-pass gate | Repair loops | Visual loop-backs | Figma read calls / cache hits | Notes |
|------|---------|----------|----------|-----------------|--------------|-------------------|------------------------------|-------|
| | | | | `<pass|fail|n/a>` | `0` | `0` | `<0 / 0>` | |
