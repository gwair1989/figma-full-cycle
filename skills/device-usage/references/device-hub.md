# Device Hub: environment and capabilities

Checked against Apple documentation and local Xcode 27.1 / devicectl 651.13.5 as of 2026-10-18. This is a baseline, not a requirement to use a particular version or model. After updates, compare local `--help`, the selected target's capabilities, and release notes for the installed version.

## Preflight

1. Compare `xcode-select -p`, any `DEVELOPER_DIR`, `xcodebuild -version`, `xcrun devicectl --version`, and the running Device Hub version. With multiple Xcode installations, a bundle ID may open another copy: select the app inside the intended Xcode by absolute path. A global toolchain switch is unnecessary for verification.
2. Select **Physical Devices** in the sidebar filter if needed; match model, OS, and UDID. CoreDevice ID is a different identifier. Info → Edit Visibility can reveal hidden properties; device names are not necessarily unique.
3. Read `device info details`: pairing, transport, connection, Developer Mode, and `capabilities`. Connectivity, developer-service readiness, screen access, and working input are separate checks. A command may return cached information even when connection failed; compare status/timestamp with a live request's result.
4. Check the required service through read-only `info` before making changes. A missing capability or a “not supported” error is not fixed by repeated reconnects. A CLI subcommand's presence does not imply physical-target support.

Examples after checking local help; set `DEVICE_ID` and `EVIDENCE` from the current run and create the evidence directory beforehand with restricted permissions:

```sh
xcrun devicectl device info details --device "$DEVICE_ID" --json-output "$EVIDENCE/device-details.json"
xcrun devicectl device info lockState --device "$DEVICE_ID" --json-output "$EVIDENCE/lock-state.json"
xcrun devicectl device info displays --device "$DEVICE_ID" --json-output "$EVIDENCE/displays.json"
xcrun devicectl device info appearance --device "$DEVICE_ID" --json-output "$EVIDENCE/appearance.json"
```

In JSON v5, information is grouped under `result.properties` (`connection`, `hardware`, `software`, `state`). The old `connectionProperties`, `hardwareProperties`, and `deviceProperties` are deprecated; account for `info.jsonVersion` and `_deprecationNotice` instead of parsing the text table. Newer CLIs support `--json-output -`, but some commands combine stdout with other data: for example, `process launch --console` requires a file. A file is more convenient for saved evidence in either case.

Read `lockState` literally: `unlockedSinceBoot` means an unlock occurred after startup, not that input is currently ready. Compare it with `passcodeRequired` and the live screen. Do not transfer framebuffer dimensions from `displays` into CUA without determining the window geometry again.

## Connection

Wired connection: USB → the normal Trust prompt on the iPhone → pairing/Developer Mode as instructed by Hub. An already paired device does not require another trust/reset. Check app installation and View Screen separately.

For new wireless iPhone/iPad pairing, Apple specifies iOS/iPadOS 27+: **+ → Pair Nearby Device…**, the same Wi-Fi network, and owner actions following the prompts. Wi-Fi operation after wired pairing is a separate scenario; Apple specifies IPv6 support on the network. If discovery fails, check the Mac app's local-network access and pairing state; do not disable the entire firewall. If connectivity is lost after an OS update, check whether pairing must be repeated.

iPhone Mirroring requirements—Apple Account, 2FA, and a locked phone—are not general Device Hub prerequisites. View Screen may work with an unlocked phone. For a camera/microphone conflict, follow [control.md](control.md) rather than declaring a USB failure.

## Inspectors and run configuration

| Hub section | What to use |
| --- | --- |
| Settings | Appearance, Liquid Glass, Text Size, accessibility, and Location supported by the specific target. Record initial values, change only within the task's scope, then restore and verify. This may change the phone itself, not just the Mac image. |
| Reports | Find a crash/diagnostic report by time and process; retrieving a list does not replace reading and symbolicating the specific report. |
| Info → Info | OS, model, identifiers, and additional properties through Edit Visibility. |
| Info → Apps | Search for the installed app and use Developer/other available filters; installation and data access depend on permissions. |
| Info → Profiles | Installed configuration/provisioning profiles; use a logging profile for a specific diagnostic task and track its expiry/removal. |
| More Actions → Show in Finder / Collect sysdiagnose | DeviceFS for accessible files and sysdiagnose for a system failure; collect only what is needed and keep raw data local. |

Start with available read-only inspectors. For environment-dependent bugs, add only relevant variants to the matrix: light/dark, normal/large Dynamic Type, Reduce Motion/Transparency, orientation. Do not automatically change every setting or assume all simulator controls apply to a physical iPhone.

Zoom changes the Mac window's scale; Resize Mode changes app-scene dimensions and requires separate support. DeviceFS/`info mountpoint` do not bypass container permissions. Download Container does not guarantee a ready-to-use `.xcappdata`: before using it in Xcode Run, verify the `<name>.xcappdata/AppData/{Documents,Library,tmp}` structure and data compatibility. For installation and diagnostics, see [deploy-and-logs.md](deploy-and-logs.md).

## Checking known issues by version

Before repeated trials, compare the installed version with a specific issue in its release notes. A “fixed” entry in a newer beta does not imply that the installed stable version includes the fix, and similar symptoms alone do not establish the cause.

As of 2026-10-18, Apple lists these fixes in **Xcode 27.2 beta 2**:

- touch/button input stopping after inactivity — `182695157` / `FB23873443`;
- incorrect modifier-key routing with multiple device windows — `177181719`;
- hardware-keyboard mode persisting for up to two minutes after disconnection — `182553164`.

For a similar failure on 27.1, save versions, idle time, the number of open windows, and control actions that distinguish possible causes. Bounded recovery from [control.md](control.md) remains the working procedure. Test a newer version as a separate experiment in an agreed environment; do not automatically update Xcode or iOS to investigate a hypothesis.

Xcode 27 notes also mention missing two-finger touch support, nonfunctional Shake, and physical-device color filters not appearing in the Hub image. These are limitations of different features; wheel/trackpad transform does not verify true multitouch. For older operating systems, separately check the minimum **input** version, not just deployment/debugging requirements: Xcode 27 has different boundaries for these capabilities.

## Sources

- [Device Hub and inspectors](https://developer.apple.com/documentation/xcode/device-hub).
- [Connecting and managing devices](https://developer.apple.com/documentation/xcode/managing-your-simulated-and-physical-devices-in-device-hub).
- [Managing apps](https://developer.apple.com/documentation/xcode/managing-apps-on-devices).
- [devicectl, JSON, and DeviceFS](https://developer.apple.com/documentation/xcode/interacting-with-devices-using-the-command-line).
- [WWDC26: Get the most out of Device Hub](https://developer.apple.com/videos/play/wwdc2026/260/).
- [Xcode 27 notes](https://developer.apple.com/documentation/xcode-release-notes/xcode-27-release-notes), [27.1 notes](https://developer.apple.com/documentation/xcode-release-notes/xcode-27_1-release-notes), [27.2 beta notes](https://developer.apple.com/documentation/xcode-release-notes/xcode-27_2-release-notes).
