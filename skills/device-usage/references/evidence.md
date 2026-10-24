# Screenshots and proof of coverage

## Choosing a source

- **Native device screenshot**: full framebuffer size, without the Hub window, sidebar, or Info identifiers. Prefer it for UI defects and visual app comparisons.
- **CUA screenshot of the Hub window**: needed for control geometry, Mac-control state, and channel diagnostics; may contain other devices and administrative details.

A native screenshot does not provide coordinates for `hub.click/drag`: CUA operates on a scaled window. After native capture, obtain a fresh CUA frame before the next coordinate action. `capture-evidence.mjs` below saves CUA bytes; for native capture, apply the same verification sequence and a separate manifest entry with `captureSource`, dimensions, and target.

The verified `devicectl 651.13.5` provides the command below; before using it, check local `--help` and the **Capture Screenshot** capability. The `EVIDENCE` directory must exist; choose a unique filename to avoid overwriting evidence:

```sh
xcrun devicectl device capture screenshot --device "$DEVICE_ID" \
  --destination "$EVIDENCE/capture-0001.png" \
  --json-output "$EVIDENCE/capture-0001.json"
```

The command was verified on a physical iPhone running iOS 27.0.1: a 1170×2532 PNG was successfully saved and inspected. This confirms that target/runtime, not every device. For multiple displays, check `device info displays` and the local `--display-unique-id` contract.

Hub's Screenshot button also captures the device's full resolution. The save path may depend on Hub preferences, the previous Simulator, and macOS; do not assume Desktop. An explicit `--destination` removes this ambiguity. [Apple capture](https://developer.apple.com/documentation/xcode/capturing-screenshots-and-videos-from-devices), [Xcode 27 notes](https://developer.apple.com/documentation/xcode-release-notes/xcode-27-release-notes).

The presence of `device capture screen-record --help` does not confirm video recording on a physical iPhone. Check the target's capabilities/limitations; when supported, use a finite `--duration`, verify file decoding, and confirm the recorder stops. Missing support is a channel limitation, not a reason to restart the device.

## Capture

Save the original CUA bytes without transcoding. Determine format from the signature, not the API name: `FF D8 FF` is JPEG; `89 50 4E 47 0D 0A 1A 0A` is PNG. Match the extension and MIME, check file existence/size, decode with an available image reader, and inspect the actual image. A signature alone does not prove the entire image is valid.

Sequence: **capture → inspect the exact saved bytes → annotate**. Assign a neutral ID before visual identification, such as `capture-0001`; until inspected, the frame stays `unreviewed` with an empty description. After inspection, record the **observed** text/state and put the expected result in the route map. A frame still showing the previous screen after a tap does not become proof of a transition because of its filename. After animation/inertia, save the final checkpoint; mark intermediate frames `transition`. `stable` is the agent's judgment based on observations, not the helper's conclusion.

Minimum manifest: channel/target/app version/build; for each capture, ID, filename, MIME, UTC observation time, `unreviewed`/`stable`/`transition`, actual content, and publication suitability. `unreviewed` does not verify a route. For live screenshots, use observation time; a timecode refers only to an existing video source. File counts include transitions and duplicates, so they do not equal the number of covered screens. Full carousel coverage requires a sequence of stable frames sharing an adjacent element, separately from boundary verification.

## Privacy

Before capture, account for automatically populated account/email/User ID/Device ID values in forms, messages, and logs. Keep raw evidence local with restricted access; include necessary reviewed excerpts in prose/public reports. Saving a file in a repository does not authorize publication.

The default classification is `raw-private`. `reviewed` means the agent checked a particular frame's suitability for the intended audience; it does not mean automatic redaction or permission to send. If personal details are present, prepare a separate authorized publication artifact while retaining its connection to the source. A composer/share sheet does not imply sending; separately record cancellation and the disposition of your new draft.

## Optional helper for CUA on Mac

[capture-evidence.mjs](../scripts/capture-evidence.mjs) uses only the Node standard library. Import it in an available CUA runtime after selecting the target and reading its documentation. Determine the actual directory from the loaded `SKILL.md` path: it may be a standalone skill or plugin cache. In the example, `skillDirectory` is the absolute path to that directory already resolved by the agent; `hub` is the already selected CUA target. `nodeRepl` is available only in the corresponding runtime; elsewhere, use the runtime's native method to inspect the saved file.

```javascript
var { createEvidenceRecorder } = await import(
  `${skillDirectory}/scripts/capture-evidence.mjs`
);
var evidence = await createEvidenceRecorder({
  directory: '/absolute/path/to/local/evidence',
  target: hub,
  session: { channel: 'Device Hub / CUA', target: 'observed model / iOS', app: 'observed app / version / build' },
});
var saved = await evidence.capture();
nodeRepl.write({ path: saved.path, entry: saved.entry });
await nodeRepl.emitImage(saved.bytes);
```

Inspect the displayed image. Set the factual caption only in the next call:

If stability is still unknown, retain `unreviewed` until another observation; do not assign `stable` merely to fill the manifest. Mark an intermediate frame observed during a transition as `transition`.

```javascript
nodeRepl.write(await evidence.annotate(saved.entry.id, {
  state: 'transition',
  observation: 'The list is still visible; the expected response has not appeared yet',
}));
```

The helper calls only `target.getScreenshot({emit:false})`, saves the exact bytes with a neutral ID, SHA-256, and `observedAt`/`savedAt`, and atomically updates `screenshots.json`. `annotate(id, {state, observation, publication?})` requires `stable`/`transition` and a nonempty observation; it changes only metadata and adds a UTC `annotatedAt`. Capture and annotate share one queue and consistently update memory/disk, including subsequent captures and recorder resumption. The capture's ID/name/bytes/hash/time and screenshot stay unchanged. To correct a caption, call `annotate` again instead of editing the manifest while the recorder is active. The previous capture API with explicit labels is retained for compatibility; use two stages for new walkthroughs. The helper cannot verify whether the agent actually inspected the image.

Format is checked by signature/end-of-file; decoding and visual assessment remain separate checks. The returned buffer contains the same saved bytes. New files use mode 0600 and new directories use 0700; existing directory permissions are unchanged.

Use one recorder/writer per directory. Reimporting/creating a recorder with the same labels continues a compatible manifest; choose another directory for a different build/channel/target. A filename collision, incompatible manifest, or leftover temporary file stops saving without overwriting original screenshots. After a write error, inspect the directory: the screenshot may have been saved before a failed manifest update; reconcile recovery with the actual files. The helper does not replace AX observations, visual verification, or existing permissions.

After the helper file is updated, an already imported module may remain cached in the runtime. If the runtime does not support module reloading, reset only the REPL bindings, select the target/read its documentation again, and import the file. This does not require restarting the app or device. Do not assume an import-path query suffix is supported without checking the runtime.

Test the helper from the skill root:

```sh
node --test scripts/capture-evidence.test.mjs
```

If the runtime does not support this import/byte-return mechanism, save through an available native tool and verify the same evidence contract; installing another control channel is unnecessary.
