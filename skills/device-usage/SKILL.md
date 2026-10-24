---
name: device-usage
license: MIT
description: Use when testing a physical iPhone from a Mac, walking app screens, diagnosing unresponsive taps or scrolling, collecting device logs, or comparing local builds with TestFlight and installed apps. Applies to Device Hub and iPhone Mirroring, not simulator-only testing.
---

# Device Usage

First identify the agent environment and available controls using [agent-compatibility.md](references/agent-compatibility.md). This skill provides instructions for Codex and Claude Code; installing it does not add Computer Use or macOS permissions. Respond in the language of the user's request.

Test a physical iPhone from a Mac using **Device Hub as the primary channel**. **iPhone Mirroring is the fallback** when Hub is unavailable or an action needs independent verification. The user's explicit choice takes precedence. The skill is independent of the repository, app, bundle ID, and iPhone model.

The current agent can complete the entire task; delegation is optional. During parallel work, the physical target and its control session must have a single input owner: only that owner navigates, changes channels, or installs/launches the app. Before handing over control, finish the current action, save a checkpoint with the target/build/channel, screen, data, and active collectors, and explicitly release control. The new owner obtains fresh AX/screenshot observations. Other agents may analyze saved evidence without controlling the phone.

## Preparation and routing

1. Record the physical target, iOS/macOS/Xcode versions, app/version/build, installation source, initial state, and permitted data changes. Account for automatic saving in inline pickers: opening an empty field may immediately assign a value without Save/Cancel. Record the initial value and permitted test-data scope before entering, then record the actual mutation afterward. Check deployment, live display, and input separately: USB connectivity or a visible screen does not prove that clicks work.
2. For initial setup, an Xcode/iOS change, or a channel failure, read [device-hub.md](references/device-hub.md): versions, pairing, capabilities, inspectors, and known limitations. For UI interaction, read [control.md](references/control.md): CUA gestures, coordinates, the available native hierarchy, text input, and recovery. For carousels and sideways scrolling, use the [horizontal scrolling](references/control.md#horizontal-scrolling) section.
3. If installation or logs are needed, read [deploy-and-logs.md](references/deploy-and-logs.md). An installed app can be tested without rebuilding; debugger/container permissions are checked separately.
4. For repeatable regression tests or an additional tool, read [automation.md](references/automation.md). Setting up XCTest/WDA is not a prerequisite for an exploratory walkthrough through Hub.
5. When saving screenshots, read [evidence.md](references/evidence.md): native device capture or CUA frames, MIME detection from bytes, neutral IDs, manifests, privacy, and the optional capture helper. Do not reuse native-frame coordinates in the CUA window.

Use available tools and their current documentation. CUA examples apply only when a compatible API is available; simulator-only tap/swipe commands do not become physical-device commands by replacing the identifier.

If Hub loses input, the agent independently performs [bounded recovery through Computer Use](references/control.md#hub-total-input-failure) within the current run, without asking again for confirmation to reconnect/relaunch. If Computer Use is unavailable or cannot control Hub, state the reason and give the user concrete remaining manual steps; do not present a recommendation as completed recovery.

Retain permissions already granted for the run; evaluate any separate purchase, consent, or new access against the actual action and CUA rules. Restore alone does not authorize a new purchase or Health access.

## Quick check of a single change

If the request concerns a single control or route, run a targeted check. Environment, initial data, and permitted-change checks remain mandatory; confirming the known target/build is sufficient. An installed app does not need rebuilding solely for this check.

1. Record the behavior under test, expected result, and required starting screen; open it through Hub. Use Mirroring under the usual fallback rules.
2. Obtain a fresh observation, perform one action, and confirm the final state. Also inspect visible labels, clipping, overlap, and element placement. Recheck loading or animation after the transition.
3. Save the actual result/evidence, observation category, and route status using the [result rules](references/deploy-and-logs.md#observation-categories). If input fails, apply the bounded diagnostics in `control.md`.
4. Finish once the result, failure, or blocker is confirmed; record data changes, stop your collectors, and close your sessions that are no longer needed. Limit coverage to this route and mark other branches `not-run`.

## Screen walkthrough

Map the agreed routes. Track authentication, permissions, subscriptions, loading, and error states separately. Existing data may make empty/onboarding states unreachable without separate preparation.

Working loop: **fresh observation → one action → verify result → checkpoint**. For evidence: **capture → inspect saved bytes → annotate**. After a sheet, resize, or rotation, wait for stable target geometry. Mac AX may omit iOS elements; confirm transitions with screenshots.

Before diagnosing, complete the input matrix from [control.md](references/control.md): Apple capability, expressibility through the current API, and the result actually verified. After a repeated no-op, compare the same input in another container; changing channels must answer a specific question. Repeatedly overshooting the middle indicates the current method's precision limit: stop trying ever-shorter drags and choose a check that distinguishes possible causes.

For a long screen, select a container and visible anchors. Move downward with overlap, confirm the end through its content, then check the reverse direction. Gesture counts and tool success do not prove coverage. If a drag skips intermediate fields, record partial coverage and use a more controllable method.

In a grid, cover both columns; in a carousel, cover every card and horizontal boundary separately from the vertical end of the page. Verify a carousel with a sequence of stable frames sharing an adjacent element; the first and last frames do not prove coverage of the middle. For auto-advance stories, record the slides actually seen and any omissions; time spent writing documentation is not content observation. Reviewing a template and auditing all content are different coverage levels.

| Symptom | Action |
| --- | --- |
| Hub: wheel scrolling does not move a long screen | Test a touch drag within the content and a reverse drag |
| Hub: live display, but app clicks and system Home are no-ops | Check [total Hub input failure](references/control.md#hub-total-input-failure) before further scroll attempts |
| Mirroring: two scroll no-ops after a sheet | Check the overlay/edge; Home → App Switcher → the same card; perform a control scroll |
| AX has not changed | Inspect the iPhone image |
| Text has not appeared | Confirm focus; test a single key instead of blindly repeating typeText |
| Mirroring reports that the iPhone is in use | The owner locks the phone; then check the connection |
| Hub shows a lock screen / app restriction | The owner performs the required standard action; record the blocker |
| CUA reports that the Mac is locked | The owner unlocks the Mac; obtain a fresh frame, then repeat the same failed control action |

After bounded recovery, verify the same input. If it still fails, use another prepared channel or record a specific blocker. Distinguish an app failure, geometry problem, input-method issue, system restriction, and stale log stream; do not claim a confirmed cause without a control check.

## Results

For each route, record entry/exit, build/channel, expected and actual results, tested scroll directions, evidence, and recovery. Statuses: passed, failed, blocked, not-run; report coverage separately, for example `status=blocked, coverage=partial` when the middle was skipped. Record the [observation category](references/deploy-and-logs.md#observation-categories) separately from route status: functional/visual defect, transient state, expected behavior, or unexpected termination. Save discovered bugs with reproduction steps and confidence in the cause.

Completion: every agreed route has a result or blocker; untested branches and final data/screen/build are recorded; your collectors are stopped; remaining sessions, backups, and caches are listed. Compare changes left behind with initial values, including defaults assigned when editors opened and content progress. Claim a complete walkthrough only within this matrix.
