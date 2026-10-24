# Repeatable scenarios and additional tools

Device Hub remains the primary channel for exploratory walkthroughs; Mirroring is the fallback. Choose an additional stack when locators, assertions, controllable gestures, or diagnostic services are needed. Installing it is not automatically part of every UI run.

| Option | Use and limits |
| --- | --- |
| Native XCTest UI runner | Elements, waits, gestures; requires a signed runner on a trusted device, but no WDA |
| Appium XCUITest + WebDriverAgent | WebDriver and repeatable scenarios; sign WDA separately from the AUT |
| Appium Inspector | Element inspection and scenario development; requires a configured server/driver/WDA |
| pymobiledevice3 | Diagnostics and additional device services; run a separate pilot and verify compatibility |

Start with the available Hub/Console/devicectl and logger. Signing the automation runner and signing the app under test are separate concerns; a preinstalled app does not automatically need rebuilding. Appium supports real-device configuration with udid, bundleId, and noReset=true. Check actual permissions separately from metadata.

For XCTest/Appium, prefer accessibility identifiers, bounded waits, hittable checks, and visible results. exists does not guarantee that an element can be tapped. For controlled velocity, investigate the current XCTest swipeUp(velocity:) / Appium mobile:swipe; still verify every gesture on the device. mobile:scroll has reliability limitations.

For repeated Appium sessions, consider reusing WDA through useNewWDA=false. If a session hangs, inspect main-thread idle state and logs first; globally disabling waits is not a universal fix.

Check versions and local --help before installation or commands. In pymobiledevice3, screenshot, syslog, display/HID, and accessibility services have different prerequisites. In the version 11.31.0 recipes, HID swipe is pointer motion without touch contact, while touch scrolling requires drag; coordinates are 0..65535, not CUA pixels. These details apply to that version, not a permanent contract. CLI availability does not prove access to all AX elements in a third-party app.

Maestro 2.11.0 does not support physical iOS devices. If considering a newer version, verify current support; a Simulator pass does not count as a physical iPhone pass.

Until a new runner/CLI has verified control taps, scrolling in both directions, logging, and recovery, treat it as an unverified candidate. Do not infer greater stability from documentation. Run different channels sequentially with separate coverage rows.

Primary sources (original research: 2026-10-15; check for updates before preparing a new stack):

- [XCTest hittable](https://developer.apple.com/documentation/xcuiautomation/xcuielement/ishittable)
- [Appium device setup](https://appium.github.io/appium-xcuitest-driver/latest/getting-started/device-setup/)
- [Appium preinstalled app](https://appium.github.io/appium-xcuitest-driver/latest/guides/capability-sets/)
- [Appium capabilities](https://appium.github.io/appium-xcuitest-driver/latest/reference/capabilities/)
- [Appium gestures](https://appium.github.io/appium-xcuitest-driver/latest/reference/execute-methods/)
- [Appium Inspector](https://github.com/appium/appium-inspector)
- [pymobiledevice3 recipes v11.31.0](https://github.com/doronz88/pymobiledevice3/blob/v11.31.0/docs/guides/cli-recipes.md)
- [Maestro 2.11.0 physical-device support](https://maestro.dev/blog/maestro-cli-2-11-0)
