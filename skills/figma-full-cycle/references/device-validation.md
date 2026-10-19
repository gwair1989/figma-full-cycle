# Physical-device validation through Device Hub

Read only when the user or project requirements call for physical iPhone checks in stages 5–7. Simulator-only work does not activate this path. The bundled `device-usage` is also an independent entry point: it needs neither Figma nor a pipeline manifest when invoked by itself.

## Bind and prepare

1. Resolve the bundled `device-usage` skill through the live catalog, retaining any plugin namespace, and record it as `physical-device-control`. Load its `SKILL.md` and the references it routes to. If it is not installed, report the missing capability for the physical checks; unrelated simulator work can continue.
2. Follow its toolchain, pairing and per-target capability checks. Use Device Hub as the primary channel and iPhone Mirroring as fallback unless the user chose otherwise. Desktop Computer Use must actually be available for autonomous UI control; installing this package supplies instructions, not a driver or permissions.
3. Record the agreed routes, app/build, baseline data and permitted changes. Keep hardware identifiers and exact target handles in the gitignored runtime file. App installation and launch follow the skill's deployment workflow and the existing authorization; a requested walkthrough of an installed app does not itself request replacing it.
4. Keep the simulator build/test binding and physical-device binding separate. A physical device identifier is not valid input to simulator-only commands. One phone does not replace the required simulator/device-size matrix.

## Execute and record

- Use fresh observation → one action → verify → checkpoint. Runtime routes in stage 7 cover the agreed success, error, cancel and back paths and relevant states. Follow the skill's bounded input recovery if Device Hub stops accepting input.
- For stage 5/6 design comparison, prefer native full-resolution device screenshots. Record capture source and image dimensions. A screenshot of the Mac's Device Hub window is control evidence, not an app render for `screenshot_diff.py`; do not compare window chrome against a Figma screen or reuse native-image coordinates for CUA actions.
- Capture → inspect the saved bytes → annotate. Only reviewed captures support screen/route coverage. Keep raw screenshots, recorder manifests and logs under `docs/.cache/<FEATURE>/device/`; the optional Node helper owns its screenshot manifest, while the main thread remains the only writer of the pipeline manifest.
- Add compact evidence to the pipeline's Physical device checks section: route, target alias/app build/channel, expected and actual result, `passed / failed / blocked / not-run`, coverage and local artifact path. Keep full identifiers and private data out of tracked prose. A blocked or partial route cannot close a required device check.
- After an implementation change, mark affected device results `stale` and rerun them. Stop collectors started for this run and report remaining sessions and data changes when finished. Report unavailable device coverage explicitly; it cannot be replaced by a successful simulator test.
