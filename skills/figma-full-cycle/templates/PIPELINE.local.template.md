# <FEATURE> — runtime state (gitignored, never in a PR)

- Worktree: <ABS_PATH>
- Simulator UDID: <UDID>
- Project/workspace: <PATH>
- Scheme / configuration: <SCHEME> / <CONFIG>
- DerivedData: <PATH>
- Baseline build/test before changes: <result; known pre-existing failures>
- Strings owning scope: <ABS_PATH_OR_NONE>
- Strings batched query / expected path::key entries files: <GITIGNORED_PATHS_OR_NONE>
- UI Plan transient context / validator logs: <GITIGNORED_PATHS_OR_NONE>
- Figma normalized node-evidence cache: <GITIGNORED_PATH_OR_NONE>
- Figma MCP transient logs / download metadata: <GITIGNORED_PATHS_OR_NONE; NO_TEMP_URLS_IN_TRACKED_FILES>
- Local keys: names only (never write values)

## Local cycle metrics

> Never move these into the tracked manifest. Fill them from what actually happened; use `n/a` when the environment does not provide the metric.

| Stage | Started | Finished | Duration | First-pass gate | Repair loops | Visual loop-backs | Figma read calls / cache hits | Notes |
|-------|---------|----------|----------|-----------------|--------------|-------------------|-------------------------------|-------|
| | | | | `<pass\|fail\|n/a>` | `0` | `0` | `<0 / 0>` | |
