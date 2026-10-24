# UI on a physical iPhone

## Connecting Device Hub

Device Hub is available in Xcode 27+. During setup or a channel failure, check versions, pairing, and capabilities using [device-hub.md](device-hub.md). Select the physical iPhone, verify its model/OS, and click **View Screen**. A nearby Simulator does not mean the phone is selected. If the visible area is limited, use the full window and **Zoom to Fit**.

Hub supports interaction with the canvas and physical device. Unlike Mirroring, it does not require the phone to remain locked. If the canvas shows a lock screen, the owner unlocks the device normally; Home does not replace authentication. The phone may remain locked after exiting Mirroring.

Compare channels sequentially: end one screen session and confirm the other is ready. Clicking a Mac menu while it is open does not click the iPhone. If Escape does not close the menu, use the AX secondary action Cancel only when it is actually available.

Apple: [Device Hub](https://developer.apple.com/documentation/xcode/device-hub), [screen interaction](https://developer.apple.com/documentation/xcode/interacting-with-your-app-in-device-hub).

## CUA and coordinates

The `cua`/`nodeRepl` examples below apply to a compatible Codex CUA runtime. In Claude Code or another runtime, use the desktop Computer Use API actually available and its documentation, following [agent-compatibility.md](agent-compatibility.md); do not call a nonexistent `cua` from a regular terminal/Node process.

Read the current CUA contract. In a compatible Codex runtime, the first call in a new session contains only app selection; read the returned documentation before further actions:

```javascript
var hub = await cua.getApp('com.apple.dt.Devices');
```

Obtain a screenshot in a separate subsequent call. Use current AX indices for Mac controls and coordinates from a fresh screenshot for iPhone content when iOS AX is unavailable.

```javascript
await hub.getScreenshot();
```

Coordinates belong to a particular window and scale, not the iPhone's physical resolution. Recalculate them after changes to the window, canvas, orientation, or sheet. Canvas size can change while the outer window bounds remain unchanged. After an animation, two observations of a stable target position help avoid a missed tap; they do not guarantee the app is fully ready.

After an action, request AX before the next decision. If AX describes only the Mac and has not changed, obtain a screenshot to assess the iOS state. Recheck a blank/skeleton first frame after a transition with a subsequent observation. Before the next coordinate tap, compare the target control's position after loading or inertia; unchanged outer window bounds are insufficient. Mark a capture of such a transition as `transition`, preserving its actual content according to [evidence.md](evidence.md).

### Native iOS hierarchy, when available

If the selected channel or an already prepared, authorized adapter provides a fresh iOS hierarchy and input, address the element by identity and its calculated `hitPoint`, preferring that point to the bounds center or an estimate from the image. Verify the target, app, and hierarchy freshness; an obscured/noninteractive bounds center may differ from an accessible tap point. If the adapter provides inspection only, a `hitPoint` does not imply a native tap command is available.

Send `hitPoint` only through the backend for which its coordinates were calculated. After a confirmed no-op, obtain a new hierarchy and screenshot and check readiness/overlap; allow one retry at an updated accessible point. If no suitable point exists or the retry fails, use coordinates from a fresh screenshot of the corresponding channel. Hub/CUA requires a new window frame: do not transfer native `hitPoint` coordinates or framebuffer pixels directly into it.

Do not treat the Hub window's Mac AX as an iOS hierarchy. An unexpanded branch/placeholder does not prove that an element is absent. Without a native hierarchy, continue the normal Hub/CUA walkthrough; this rule does not require installing another backend or connecting Xcode MCP.

## Hub gestures

### Input matrix

For each required gesture, maintain three independent columns. Record versions and the actual runtime contract; Apple support does not prove availability through CUA.

| Method | Apple capability | Expressibility through the current API | Verified result |
| --- | --- | --- | --- |
| Contact drag | Click/drag in Device Hub | For example, start/end only; no duration/path | Container, direction, before/after anchors, no-op/opening/overshoot/precise transition |
| Wheel/trackpad scroll | Separate scroll path; not equivalent to direct touch | Supported axes/distances; the source device type may be unknown | Test separately after previous inertia stops |
| Key and scroll combination | For Mirroring, Apple describes holding Shift while scrolling | Only if the API expresses a held key/modifier throughout the scroll | Sequential press/release followed by scroll does not verify the combination |
| Touch and hold / double-tap | Click-and-hold / double-click | In compatible Mac CUA: `click([x,y], {durationMs: ...})` / `{clickCount: 2}` | Check the menu/state; click duration does not add duration/path to drag |

In Xcode 27, Apple describes a hybrid model: a click produces `UITouch.TouchType.direct`, the wheel produces `UIEvent.EventType.scroll`, and trackpad pinch/rotate produces `UIEvent.EventType.transform`. A working drag and failing wheel can therefore be expected to differ. For pointer scenarios, check whether **Device → Simulate Trackpad or Mouse** is available for the selected target; do not compensate for its absence with an invented command. Xcode 27 notes state that Hub does not support two-finger touch. These Apple capabilities do not automatically expand the CUA contract.

A `pressKey` duration, two parallel commands, or an unknown key alias do not by themselves prove overlapping events. Do not guess undocumented aliases or replace CUA with hidden event injection. Apple sources describe Hub's hybrid input model; actual UIEvent/UITouch events inside a third-party app are unknown without instrumentation. See [Xcode 27 release notes](https://developer.apple.com/documentation/xcode-release-notes/xcode-27-release-notes) and [TN3210](https://developer.apple.com/documentation/technotes/tn3210-optimizing-your-app-for-iphone-mirroring).

### Precision and boundaries

To reach lower content, perform a contact drag from bottom to top within one scroll container. The coordinates below are variables selected from the current screenshot:

```javascript
await hub.drag([contentX, lowerY], [contentX, upperY]);
await hub.getAXState();
await hub.getScreenshot();
```

In the verified CUA API, drag accepts only start and end points, with no duration. A short drag may cause significant inertia; calibrate using visible anchors rather than pixel counts. Test a reverse drag, and perform horizontal drags inside the intended carousel.

Before a gesture, identify noninteractive areas **within this container**. A drag starting inside a card/button is sometimes interpreted as opening it. In a grid, the gap between columns may suit a vertical drag; in a horizontal row, the same position may already contain the next partial card. The right margin on another screen may contain an info button; do not reuse its coordinate without a fresh observation.

If a tap is needed to stop inertia, select an observed empty area, then obtain AX and a stable screenshot. Without such an area, wait for stability through observations or change methods. Shortening a drag alone does not guarantee a small displacement. Test wheel-style scrolling as a separate action after stabilization: continued drag inertia does not prove the wheel works.

If wheel-style scrolling is a no-op while more content is visibly available, test a touch drag. These are different input methods. When the middle is skipped, bounded calibration against anchors is allowed. If shortening the drag yields the same overshoot or alternating no-op/overshoot, stop: this is a precision limit of the method in the current state, not proof of an app defect or the drag's physical speed. Next use another verified method, a control container, or an owner-performed manual check if the task requires it.

Techniques verified on an iPhone 13 with Xcode 27 are not guaranteed for all iOS versions/adapters. Success through one channel does not automatically apply to every button, app, and state.

### Horizontal scrolling

1. After inertia stops, identify the horizontal container, its visible cards, and an internal gesture strip from a fresh frame. Both contact-drag endpoints must stay within that row at roughly the same height; avoid the system screen edge and drag handles. If no empty strip exists, select an observed card area and verify that the gesture scrolled the row instead of opening or dragging the card.
2. In Hub, test a contact drag in the chosen horizontal direction, then reverse it from an observed position. Confirm content direction and card order with frames: RTL, paging, and nested vertical scrolling can change the outcome. Vertical scrolling elsewhere on the page does not verify this axis.
3. Record each gesture's result: movement of adjacent cards, card opening, vertical displacement, no-op, or overshoot. If a shorter drag again overshoots the middle, stop calibrating that method. When the API accepts only start/end points, a short path does not set a low speed; do not add duration/path parameters from another API.
4. If the current API documents horizontal `scroll`/a left-right axis, test it separately after the contact drag stops, with a supported small distance. It may behave differently because it is another input method. After a no-op, test the same method and axis in another observed horizontal container if such a control is available. Working Home input with a failing carousel does not by itself justify general Hub recovery.
5. If an already prepared adapter actually supports touch-swipe duration or a trajectory, a separate trial may use those parameters and a new checkpoint. This capability does not belong to every `drag`. Without a controllable method, retain `coverage=partial` and a blocker for the dependent route; choose any further owner-performed manual trial or prepared channel for a specific check that distinguishes possible causes.
6. To prove coverage, save a sequence of stable, overlapping frames: the same element must be recognizable in adjacent frames. For each step, record visible cards, direction, and evidence ID; separately confirm both ends and the reverse direction. Leave a skipped middle range `partial` even when the outermost cards are known. Do not infer the total card count from two endpoint frames.

If contact swipe works but indirect scrolling fails in the same control, and app source is available, inspect scroll-event handling and `UIPanGestureRecognizer.allowedScrollTypesMask` (`.continuous` / `.discrete` / `.all`) for the actual input source. This is a diagnostic direction, not a cause established by one no-op. Apple distinguishes these event types in [TN3210](https://developer.apple.com/documentation/technotes/tn3210-optimizing-your-app-for-iphone-mirroring).

## Text

First open the field, confirm focus/readiness through observation, then type. A batch of “navigate → typeText” may outrun the UI. An absent software keyboard does not imply absent focus.

If typeText produces no visible text, test an ordinary key once through pressKey in a safe empty draft. In Hub, separately check **Capture Keyboard** using current AX; this toggle is not a universal fix. Delete the diagnostic character and cancel the draft; restore any temporary Capture Keyboard change to its initial state.

After switching full ↔ compact, reconfirm Capture Keyboard: changing windows may reset it to off. A previous on state and a banner in another window do not confirm current routing. If compact AX does not expose the toggle, check it in the full window and verify key delivery in the window used for the test.

Distinguish **Keyboard Capture**, **Simulate Hardware Keyboard**, and **Toggle Software Keyboard** in Device → Keyboard. The first routes Mac keys, the second simulates a connected hardware keyboard, and the third controls software-keyboard visibility. Capture being off outside a text-input scenario is not a configuration error. On affected versions, the software keyboard may take up to two minutes to appear after Hardware Keyboard is disabled; Apple lists a fix in 27.2 beta 2. Do not change the text field or restart the AUT solely because of this symptom.

If an ordinary key works but Hub intercepts a shortcut, inspect the documented `hostKeybindingPolicy` setting in the `com.apple.dt.Devices` **container**. Read-only: `defaults -container com.apple.dt.Devices read com.apple.dt.Devices hostKeybindingPolicy`. A missing key means no explicit override, not an established value of 0. Apple describes values 0 (rich shortcuts), 1 (minimal while interacting with the device), and 2 (minimal shortcuts). A change requires justification and recording the previous override or its absence; do not apply it globally as a universal fix. With multiple device windows, account for issue `177181719` from the [version-specific notes](device-hub.md#checking-known-issues-by-version).

`typeText`, hardware key events, and paste are separate methods. A single successful input does not verify automatic clipboard synchronization; do not transfer old Simulator settings to Hub. Test paste with nonsecret text and account for the current CUA runtime's clipboard.

Do not classify a field as broken based on one input method. Search and an editing form may behave differently; confirm the result in each field.

For an inline picker, first record the initial value, then observe the value immediately after opening and after leaving. There may be no separate confirmation button: even an empty field can save a default. Compare this with permitted test changes; reentering verifies persistence but may itself change data.

## Fallback channel: iPhone Mirroring

Mirroring requires compatible Mac/iPhone devices, the same Apple Account with 2FA, Wi-Fi/Bluetooth, nearby devices, and a locked iPhone. Check requirements and regional availability with [Apple Support](https://support.apple.com/en-us/120421). USB alone does not make Mirroring wired. AirPlay, Sidecar, and Internet Sharing may prevent connection.

After a manual action on the phone, the owner locks it again. An “iPhone in use” message indicates a connection state, not an app freeze.

```javascript
var phone = await cua.getApp('com.apple.ScreenContinuity');
```

After reading the documentation, obtain a screenshot in a separate call. For vertical movement, use a supported scroll:

```javascript
await phone.scroll([contentX, contentY], 'down', 1);
await phone.getAXState();
await phone.getScreenshot();
```

On macOS, this API's numeric distance is in pages, not pixels; start with 1 and measure the actual movement. An argument of 300 does not mean 300 px. The supplied distance may not produce linear displacement.

For horizontal scrolling in Mirroring, first check the actual API contract: a separate horizontal axis/direction or holding Shift while scrolling. The latter is [described by Apple](https://support.apple.com/en-us/120421). Sequentially pressing/releasing Shift and then scrolling is different input; without documented overlap, do not substitute parallel calls for holding the key. If the API expresses neither a horizontal axis nor modifier+scroll, record horizontal input as unavailable through that method. Do not transfer the Hub drag recipe to Mirroring; Hub remains primary, but after switching channels, separately verify the same axis and control result using the matrix.

### Recovery after a no-op

1. Check a fresh frame, overlay, keyboard, Mac menu, correct container, and list boundary. A reverse gesture distinguishes the end of content from input loss.
2. After two no-ops in the correct container, allow one safe focus click and a control scroll. If that does not help, proceed to the next step.
3. Test the same method in another observed container on the same channel: preferably a standard system control with the same axis, then the original container. Working vertical input does not verify horizontal input. Success in the control container narrows the problem to the target's context; a general no-op leaves channel/focus/API among the possible causes. If such a control is unavailable, record `not-run` instead of replacing it with another repetition of the previous action.
4. If Mirroring shows signs of input loss, perform **Home → App Switcher → the same app card**. Confirm each transition separately:
   - pressKey('super+1') → AX/screenshot of Home;
   - pressKey('super+2') → AX/screenshot of App Switcher;
   - click the current card → AX/screenshot of the previous screen;
   - one scroll and a reverse movement → compare anchors.
5. This cycle brings the app back from the background without force-quitting it. Switching internal tabs does not replace the cycle. Verify whether App Switcher alone is sufficient through the result, rather than assuming it.
6. If one cycle does not restore input, save evidence and check lock/connection state. Reconnect or change channels for a specific check, such as distinguishing loss of the entire session from a no-op in one method. Record the expected distinguishing result and compare the same action. If the new channel offers no different input capability or control, do not repeat an exhausted trial merely to switch channels.

For Hub, after checking geometry/menu/target, repeat one content drag; after a no-op, apply the same control-container check and channel-switch criterion. Channels may share the Mac, iPhone, app, and CUA, so their comparison is not fully independent. A successful reconnect without a working control action does not establish recovery. Do not change global mouse/scroll settings or reinstall the app without separate justification.

### Hub: total input failure

If Hub's Mac controls work and the image is visible, but an ordinary app click **and system Home** produce no transition, scroll trials do not yet characterize an individual carousel.

Compare the version and idle time with issue `182695157` / `FB23873443`: Apple lists a fix for touch/button input loss after inactivity in Xcode 27.2 beta 2. On an older version, this is a testable hypothesis, not an established cause; save timing and control results. See the [version check](device-hub.md#checking-known-issues-by-version).

When Computer Use is available, the agent performs this procedure itself, without requesting renewed confirmation for these actions within the current run. Do not stop at advice when the agent can control Hub. Use the current CUA contract, fresh AX/screenshots, and observed controls; observe the result after each action.

1. Verify target/geometry/menus and save a checkpoint. Through **More Actions → Stop Screen Sharing**, then **View Screen**, reconnect the same physical target once.
2. Repeat the exact failed **Home** action, return to the app, and test an ordinary safe click with a visible result. If both actions work, finish recovery and continue the interrupted route.
3. If input is still unavailable, check that closing Hub will not interrupt other people's needed sessions. Perform a normal **Quit of Device Hub itself** through the app menu, reopen the same Hub copy through Computer Use, and select the previous physical target → **View Screen**. Keep the app running on the iPhone. If running simulators must be preserved and **Quit and Keep Simulators Running** is available, use it. If another active session faces a specific risk, stop the relaunch and report the blocker.
4. Test Home and an ordinary click again. Recovery is confirmed only by visible transitions for both controls. If they remain no-ops, save the blocker and do not loop relaunches; choose another prepared channel if it suits the task.
5. After recovery, separately test the required horizontal input from an observed middle position. Restored Home/click input does not prove drag precision or wheel support.

If Computer Use is absent, unavailable in the current session, or cannot observe/control Hub, explain the limitation directly and give the user **only the steps not yet completed**. For fully manual recovery, use this instruction:

> I cannot currently control Device Hub through Computer Use: <specific reason>. Please perform: More Actions (…) → Stop Screen Sharing → select the same iPhone → View Screen. Test Home and an ordinary tap in the app. If that does not help, quit Device Hub completely through the app menu, reopen it, and repeat the connection and checks. Report whether both actions now work.

Do not ask the user to repeat an exhausted reconnect/relaunch solely because CUA is unavailable. If only a Mac/iPhone unlock is needed, request that specific action using the section below. When Computer Use returns after manual recovery, obtain fresh AX/screenshots and verify the same input. If the tool is still unavailable, record the owner's result as `reported-by-user`, autonomous verification as `not-run`, and leave the dependent UI route blocked. Preserve the checkpoint for resuming.

This is bounded channel recovery, not a restart of the app/phone under test or an established fix for horizontal inertia. Determine the cause of failure and any relationship to the owner's preceding physical input through separate controls.

### Mac locked and iPhone lock screen

The CUA error `Mac locked` concerns the host; a lock screen on the canvas concerns the iPhone. Save the last confirmed screen and unfinished action, and request a normal unlock of the corresponding device. After the owner responds, obtain fresh AX/screenshots, verify target/screen and geometry, and repeat the exact failed control action. Its visible result confirms recovery. The owner's statement that the device is unlocked is insufficient; reconnect/reset is unnecessary after input has been successfully restored.

For Screen Time/App Limits/an app blocker, record the system restriction: working Home input or another app helps distinguish it from channel loss. The owner removes the restriction through the normal process within the agreed run. Passcodes and bypassing protections are outside UI recovery.

Relaunch, reboot, pairing reset, and reinstall have different consequences. Preserve state and logs before the minimum necessary intervention; deleting the app/data is not a routine fix for broken scrolling.

## Observation limits

Do not consider camera/microphone/Face ID verified through Mirroring. In Hub, sensor apps may interfere with View Screen or produce blank video/silence; Phone/FaceTime may interrupt interaction. Test sensor scenarios separately on the device. [Apple](https://developer.apple.com/documentation/xcode/interacting-with-your-app-in-device-hub)

Hub documents physical-device screenshots, but its built-in video recording section concerns simulated devices. Newer CLIs include `device capture screen-record`; this does not prove support on a physical iPhone. Check capabilities and the actual result. A native screenshot and a CUA window frame serve different purposes; see [evidence.md](evidence.md). [Apple capture](https://developer.apple.com/documentation/xcode/capturing-screenshots-and-videos-from-devices)
