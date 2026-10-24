# Agent compatibility

The skill consists of instructions and an optional evidence helper. It does not install a control driver, MCP server, hooks, or access permissions. Use only tools provided by the current environment, with their actual permissions. Tool rules and user-selected constraints take precedence over the skill's examples.

## Codex

Invoke the standalone skill with `$device-usage`. In Codex desktop, when `cua_repl` is available, select the app, read the returned documentation, then use `cua` as described in [control.md](control.md). Having Codex CLI or shell execution alone does not imply desktop Computer Use is available.

When installed as part of a plugin, the name may include the package namespace, such as `figma-full-cycle:device-usage`. Select the exact name from the current session's catalog. This skill can be invoked independently of the package's other skills: it requires neither a Figma link nor a full-cycle run.

## Claude Code

A standalone skill in `~/.claude/skills/device-usage/` or `.claude/skills/device-usage/` is invoked with `/device-usage`. For a plugin installation, the namespace depends on the package name, such as `/device-usage:device-usage` in the original plugin. Check the actual name in the current Claude Code version's available-skills list.

1. Check the provided tools: access to native Mac apps, a fresh screen, and input is required. Browser-only automation cannot control the Device Hub window.
2. If the environment or a configured MCP provides desktop Computer Use, read its contract and perform observe → act → verify through that API. The names `cua`, `hub`, and `nodeRepl` in Codex examples are not built-in Claude Code APIs.
3. If Computer Use is unavailable, continue permitted read-only diagnostics through `devicectl` and local-file analysis. For UI actions and input recovery, give the owner concrete steps from [control.md](control.md#hub-total-input-failure), save a checkpoint, and explicitly state that autonomous UI verification is unavailable.
4. Do not substitute hidden event injection, AppleScript, or macOS permission changes for missing Computer Use. If the user separately chooses another tool, follow its documentation and the agreed scope.

Perform input recovery autonomously only when a suitable tool is available and the scenario is authorized. Agent confirmation cannot replace the owner's Unlock/Trust/new-access actions. Keep the user's report of manual success as `reported-by-user` until the agent can verify the result itself.

## Portable paths and evidence

All links within the skill are relative to its `SKILL.md`. Resolve the helper's absolute path from the current installation; do not assume a username, `~/.agents`, `~/.claude`, or plugin-cache location.

`capture-evidence.mjs` works with an object whose `getScreenshot({emit:false})` returns a `Uint8Array`. Installing the plugin does not provide that object. If the runtime does not provide it, save the screenshot with a native tool and verify the file and manifest separately. Native `devicectl` capture is also available when supported by the selected target.

Use one active installation method per agent: standalone or plugin. Do not automatically create a second copy during an update or overwrite the user's local changes.

Primary sources: [Claude Code skills](https://code.claude.com/docs/en/skills), [plugins](https://code.claude.com/docs/en/plugins), [marketplaces](https://code.claude.com/docs/en/plugin-marketplaces).
