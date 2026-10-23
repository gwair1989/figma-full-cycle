# Visual validation context and reports

Shared setup and evidence contract for `figma-design-compare` and `swiftui-adaptivity-check`.
`<shared-root>` is the sibling `_figma-full-cycle-shared` directory. It is installed once,
has no `SKILL.md`, and is not an invocable skill.

## Invocation modes

- **Standalone:** accept the project root, selected screens/states or supplied native captures,
  and requested configurations/output path. No pipeline manifest, UI Plan, feature branch,
  commit or completed earlier stage is required. Write the report in the user's language. Keep
  captures, comparison JSON and logs under `docs/.cache/<RUN>/` or the user's artifact directory;
  identifiers and private data stay local.
- **Pipeline:** reuse the caller's project/UI contracts, screen mapping, Figma pin when applicable,
  artifact root and relevant manifest sections. Consume the UI Plan when provided. Return report
  path, gate result, findings, evidence and affected rows. The orchestrator alone updates its
  manifest, chooses loop-backs and commits; reading a manifest does not authorize writing it.

In shared references, record-in-**manifest** requirements use the standalone report when no
pipeline is active. Stage scheduling and UI Plan bookkeeping apply only to pipeline calls.
Standalone checks derive constraints and relational invariants from project docs, the brief and
relevant views; missing evidence stays an explicit question or gap.

## Setup and scope

1. Read project instructions. Reuse current supplied contracts; otherwise resolve affected areas
   through [project-ui-conventions.md](project-ui-conventions.md), recording sources. Inspection
   does not select/change architecture. Before authorized fixes needing an architecture decision,
   use project documentation or an existing user decision; resolve absent/conflicting choices.
2. Discover available build/run, preview, capture and optional visual-review tools, or reuse caller
   bindings. Use exact registered names including namespaces. Reinvoking the owning skill is not
   a visual-review fallback.
3. Existing native screenshots need no rebuild. Record build/source, device, configuration and
   freshness; supplied captures cover only recorded rows. For live capture resolve the scheme
   and actual runtimes and serialize builds. Missing access blocks affected rows only.
4. Use Figma only for required/optional design evidence, following
   [figma-mcp-acquisition.md](figma-mcp-acquisition.md). No-design adaptivity performs no Figma
   discovery/authentication and needs no token or mock.
5. Physical iPhone checks run only when requested/required. Discover bundled `device-usage` by its
   registered name and follow it: Device Hub primary, iPhone Mirroring fallback unless the user
   chose otherwise. Missing control leaves required physical rows blocked; simulator results do
   not close them. Native app captures support geometry; window captures are control evidence.
   One phone covers only its own matrix rows.

Default to inspection/reporting. Fix only within authorization from the user or pipeline call,
then rerun affected captures/checks. Follow project UI contracts and preserve Accessibility scope;
add it only on an explicit requirement. Unresolved findings do not widen the change. Standalone
validation does not create branches, commits, PRs or Figma mutations.

## Report contract

Write one Markdown report with:

- Scope/mode, project/build, checked-at time, requested screens/states/configurations and sources.
- Resolved constraints/deviations; a Figma pin only when design evidence is used.
- One row per screen/state/configuration: target; native capture source, dimensions and path;
  mechanical command/result/JSON path or explicit `not-run` reason; reviewed evidence, findings,
  required measurements and final status.
- Findings, authorized fixes/rechecks, pending translations, blockers and uncovered scope.

Row statuses: `passed / failed / blocked / not-run / stale`. A saved image becomes evidence only
after its bytes have been opened and inspected. Preserve initial/repeated results after fixes;
changed UI/copy/build inputs invalidate affected rows until recaptured and rechecked.

Overall `passed` requires every required row to meet the owning skill's completion criteria.
Otherwise report `failed` or `blocked` with missing coverage. An audit can finish with failed
validation. Record actual helper markers; skipped geometry never gets a fabricated clean marker.

Raw payloads, screenshots and full logs stay in the artifact directory. Return compact results
and paths, not catalogs or tool responses. Per-screen review may use independent agents when
available; the current agent can perform the same documented visual review itself.
