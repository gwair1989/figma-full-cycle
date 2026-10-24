# Installation, diagnostics, and completion

For toolchain, capability, and JSON v5 checks, start with [device-hub.md](device-hub.md). Do not parse the human-readable `devicectl` table as a stable format.

## Choosing a build

Save the current version/build, installation source, and data state before replacement. Distinguish configuration (Debug/Release) from signing channel (development/Ad Hoc/App Store/TestFlight). A Release build may be development-signed.

To investigate an installed app without replacing it, available read-only metadata/UI information is sufficient. An empty targeted app query does not prove the app is absent: check `device info apps --help`, retrieve `--include-all-apps` if necessary, and locally extract the intended bundle ID from JSON. In the verified CLI version, this flag ignores other filters; the full list contains unrelated apps and identifiers, so include only minimal target-app information in the report. `builtByDeveloper=false` does not distinguish App Store from TestFlight; leave an unknown installation source unknown.

For local installation, use the current project's build/run script if suitable and follow its cache-lifecycle rules. Otherwise prepare a device build through xcodebuild using the existing workspace/project, scheme, target, signing team, and reusable DerivedData. Do not reuse details from a previous project.

The commands below are templates; set variables from the discovered environment. DEVICE_ID is for devicectl; UDID is the hardware identifier for libimobiledevice. Check the CLI's current --help and JSON schema.

```sh
xcrun devicectl list devices --json-output "$EVIDENCE/devices.json"
xcrun devicectl device info apps --device "$DEVICE_ID" \
  --bundle-id "$BUNDLE_ID" --include-default-apps \
  --json-output "$EVIDENCE/app-before.json"
```

In a list with multiple devices, explicitly match hardware UDID, CoreDevice ID, and model. DeveloperApp/ContainerAccessible metadata does not prove installation source, get-task-allow, or actual debugger/container access after replacement with TestFlight.

If a copy of an accessible container is needed before replacement:

```sh
xcrun devicectl device copy from --device "$DEVICE_ID" --source . \
  --destination "$BACKUP_DIR" --domain-type appDataContainer \
  --domain-identifier "$BUNDLE_ID" --timeout 120
```

Check the exit status and result. An app-container copy is not a full device backup; it excludes some Keychain/iCloud data, may be inconsistent during active writes, and is not available for every app. Restrict local permissions on the copy. Do not promise rollback without the original build, compatible data, and a verified restore.

For a development build with suitable capabilities, ordinary command-line overrides may be used: CODE_SIGN_STYLE=Automatic, DEVELOPMENT_TEAM, CODE_SIGN_IDENTITY="Apple Development", and an empty PROVISIONING_PROFILE_SPECIFIER. Do not blindly transfer conditional CLI settings such as SETTING[sdk=...]=... from .xcconfig: check effective values. Perform provisioning updates within the available account and request scope. A one-time installation does not require changing the repository's Release settings.

Check the signing identity, embedded profile, ProvisionedDevices/expiry, and required entitlements. Successful compilation does not prove installability. Error 0xe800801f with the text Beta profile without proper entitlement requires profile/entitlement investigation, not a reinstall loop; a code alone does not identify a universal cause.

Resolve APP_PATH from TARGET_BUILD_DIR + WRAPPER_NAME for the correct target, and obtain the bundle ID from the product. Installation and launch are separately verifiable steps:

```sh
xcrun devicectl device install app --device "$DEVICE_ID" \
  --json-output "$EVIDENCE/install.json" "$APP_PATH" \
  > "$EVIDENCE/install.log" 2>&1
```

After successful installation, confirm the version/build, then launch:

```sh
xcrun devicectl device process launch --device "$DEVICE_ID" \
  --json-output "$EVIDENCE/launch.json" "$BUNDLE_ID" \
  > "$EVIDENCE/launch.log" 2>&1
```

Verify the data and expected screen. For TestFlight/App Store/third-party apps, preserve the user's chosen channel; external UI control does not automatically require rebuilding the AUT. Uninstall deletes data and does not replace an update.

[Apple CLI](https://developer.apple.com/documentation/xcode/interacting-with-devices-using-the-command-line), [Developer Mode](https://developer.apple.com/documentation/xcode/enabling-developer-mode-on-a-device).

## Logs

| Source | What to check |
| --- | --- |
| Hub → Reports | Time/process/build of a specific crash report; the list is not a live log |
| Console on Mac | Correct iPhone, Start, process/subsystem filter, fresh events |
| idevicesyslog | Compatible CLI, hardware UDID, actual process name, file updates |
| devicectl launch --console | stdout/stderr from a new launch; not the complete unified log |
| Crash/Jetsam report | Time, build, termination reason, matching dSYM for symbolication |

Before installing a new diagnostic stack, check built-in Reports, More Actions → Show in Finder (DeviceFS), `device info mountpoint`, and the available `systemCrashLogs` domain. For a system failure, use Collect sysdiagnose / `device sysdiagnose --help` if needed; this is a separate collection with time and resource costs, not a mandatory step in every UI test. Profile information is available in Info → Profiles; track a logging profile and its removal separately. DeviceFS does not expand app-container permissions.

If libimobiledevice is already available, run a foreground collector in a managed session and record its ID/PID:

```sh
idevicesyslog -u "$UDID" -p "$PROCESS_NAME" --no-colors \
  > "$EVIDENCE/device-process.log" 2>&1
```

Perform UI actions from another session. After install/relaunch, check new timestamps and a known logged action. A live PID or nonempty file may belong to a stale stream. For stale capture, restart only your collector and repeat the check; an empty log does not prove the absence of errors.

For a new launch with stdout/stderr, when the scenario permits launching:

```sh
xcrun devicectl device process launch --device "$DEVICE_ID" --console \
  --json-output "$EVIDENCE/console-launch.json" "$BUNDLE_ID" \
  > "$EVIDENCE/app-stdio.log" 2>&1
```

This flag does not reattach streams to an existing process. --console waits for process termination and forwards catchable signals to the app: Ctrl-C may change the AUT lifecycle. Use a file for --json-output, not stdout '-'; check the contract for your CLI version.

Error/Fault severity from a system framework within the process is not automatically an app bug. Correlate it with the action, time, and symptom. Signal 9 during install/replacement also does not prove a crash. Keep raw logs, identifiers, personal photos, and account data local; include only necessary sanitized excerpts in the report.

[Console](https://support.apple.com/guide/console/view-log-messages-cnsl1012/mac), [crash reports](https://developer.apple.com/documentation/xcode/acquiring-crash-reports-and-diagnostic-logs), [idevicesyslog](https://github.com/libimobiledevice/libimobiledevice/blob/master/docs/idevicesyslog.1).

## Coverage manifest and bugs

### Observation categories

The category describes what was observed; `passed/failed/blocked/not-run` status and coverage describe verification of the agreed route. Record them separately.

| Category | What to confirm |
| --- | --- |
| Functional defect | A persistent discrepancy from the expected action/data/navigation while the input channel works. One no-op without control actions does not yet establish an app bug. |
| Visual defect | Overlap, clipping, incorrect placement/color, or unreadable text after the UI stabilizes; save the frame and configuration. Record it even when the primary function works. |
| Transient state | Loading, animation, keyboard appearance. Obtain the next observation; if the expected transition does not finish within the scenario, record the unmet expectation and investigate the cause. |
| Expected behavior | The state matches the agreed scenario. An empty state, disabled button, or permission dialog is not automatically a failure or success: compare it with the expected behavior of that specific state. |
| Unexpected termination | The app disappeared/the process terminated contrary to the scenario. Correlate UI, PID, and fresh logs; separately establish a crash, Jetsam, system termination, or planned relaunch. A PID change alone does not prove a crash. |

When input is unavailable, a system restriction applies, or the final state cannot be verified, record a blocker and actual coverage. Do not turn an infrastructure blocker into an app functional defect. Use `failed` for a confirmed discrepancy; do not assign a final `passed` to a transition before its final observation.

```markdown
Run: <date/time/timezone>; device/iOS/macOS/Xcode/tools: <versions>
App: <bundle ID/version/build/source>; install: <outcome/evidence>
Initial state/data: <fixture or existing>; allowed changes: <scope>
Hub/device configuration: <appearance/text size/accessibility/location/orientation; keyboard modes; relevant overrides>
Logger: <source/session/verified freshness>
| Route/state | Entry → exit | Checks, scroll ↓/↑/←/→ | Observation/category | Status/coverage | Evidence | Recovery/blocker |
| --- | --- | --- | --- | --- | --- | --- |
| ... | ... | ... | actual/category | passed/failed/blocked/not-run; actual coverage | ... | ... |
Uncovered: <states and reasons>
Final: <screen/data/build/configuration restored or remaining changes>; sessions: <stopped/remaining>; backups/cache: <disposition>
```

For a bug, save build/channel, initial state, exact steps, expected/actual results, reproducibility, evidence, and confidence. Clicking an empty part of a row versus its text, changing scale, and using another channel are different control conditions. Agreement between Hub and Mirroring strengthens the hypothesis, but shared CUA is not yet excluded; a physical touch or XCTest can help isolate the cause.

Close test drafts without saving unless saving was part of the scenario; stop your own collectors while accounting for signal forwarding. List remaining screen sessions, build, data changes, backup, and build cache. Do not clean other people's or unknown caches.
