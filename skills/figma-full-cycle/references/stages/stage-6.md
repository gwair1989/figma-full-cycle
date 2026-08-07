# Stage 6 — Adaptivity

**Read before starting** (skip what the session already holds): LAY-11 of [`../layout-adaptivity-contract.md`](../layout-adaptivity-contract.md).

## Role binding

Build the matrix from the deployment target plus the spec, Strings, Layout and Accessibility contracts, per LAY-11:

- The **smallest supported device** and the largest.
- Devices **with and without a home indicator** — a different bottom safe area is a distinct bug class.
- Light/dark.
- The content sizes supported by the Typography contract.
- Documented locales and directions, and long copy.
- Orientations if supported.
- Keyboard and safe area.

Rules:

- Check pending translations only with a sanctioned pseudolocale or fixtures, or leave a pending translation gate or waiver per project policy — never generate substitute translations.
- Add AX/VoiceOver/Reduce Motion/increased contrast only under an active Accessibility contract.
- Bring the screen up directly. A screen with geometry keeps at least two `#Preview`s — smallest and largest supported device — because the default preview is the reference device and proves nothing.

## Fallback

No device → the minimal available one.

## Gate

- Every row required by the resolved contract shows no clipping or overlap.
- Per required device the screenshot evidence explicitly confirms: the layout fits the screen, no unintended letterboxing, no clipped content, background reaching the edges.
- Translation readiness tracked separately from the source gate.
- Evidence stored.
