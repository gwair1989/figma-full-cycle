# Layout & Adaptivity Contract

The sixth area of the project UI convention contract. The goal is to fix **which layout API** the feature is built with, so the screen adapts to every supported size by itself instead of being tuned with numbers for one device.

**Read it in full at the start of stage 3** — the stage that enforces LAY-01…LAY-10 — and keep it in session for stages 5, 6 and 8. The preflight audit does not read this file: it resolves the `Layout` row from the baseline digest in [`project-ui-conventions.md`](project-ui-conventions.md), and reads this contract early only when that row cannot be resolved without it.

The area resolves with the same statuses as the others: `matched / project-specific / skill-fallback / inferred-from-code / conflict / not-applicable`.

## 1. What to resolve from the project

Search by terms as well as section names: `layout`, `adaptive`, `GeometryReader`, `geometry`, `safe area`, `ignoresSafeArea`, `reference canvas`, `artboard`, `designWidth`, `designHeight`, `scaleEffect`, `padding`, `spacing`, `Spacer`, `deployment target`, supported devices and orientations.

Record in the manifest:

- the design reference canvas (artboard size) and the **permitted** way to map it to runtime (a project API such as `designWidth/designHeight`, or native layout);
- the smallest and largest supported device;
- layout patterns the project explicitly forbids (a legacy note in documentation is a rule, not an observation);
- supported orientations.

**Precedent in code never outranks documentation.** When existing screens use one approach while documentation marks it legacy or forbidden for new screens, the documentation wins and copying the legacy screen is prohibited; only a genuinely ambiguous wording becomes a `conflict`. `inferred-from-code` is acceptable for this area only when there is no documentation at all.

## 2. Baseline rules

The baseline applies unless the project defines a more specific compatible rule.

### LAY-01 — no fixed canvas

Never build a screen as a fixed-size artboard that is scaled as a whole:

```swift
// forbidden
content
    .frame(width: 393, height: 852)
    .scaleEffect(min(w / 393, h / 852))
```

That is an aspect-fit of the artboard: a different aspect ratio produces letterboxing, not adaptation. The screen container stretches instead: `.frame(maxWidth: .infinity, maxHeight: .infinity)`.

Detection: `.frame(width:` / `height:` with a number equal to the reference canvas size next to `.scaleEffect(`.

### LAY-02 — no hard frame on `Color` and shapes

`Color`, `Rectangle` and `RoundedRectangle` are already greedy: they take whatever size is proposed. A hard `.frame(w, h)` on them does not stretch, it **shrinks**. A background is a plain `Color` without a frame, or `.background(...)` on the container.

Detection: `Color`/`Rectangle`/`RoundedRectangle` plus `.frame(` with numeric `width:`/`height:`.

### LAY-03 — no hard or derived screen-level sizes

Forbidden: `.frame(width: 393)`, `.frame(width: 393 - 32)`, `.frame(width: geo.width - 32)` used to create an inset. An inset is expressed with padding, never by subtracting from a width.

Fixed sizes are allowed only for genuinely fixed elements (icon, avatar, a control with a defined size) and come from design context, not from eyeballing.

Detection: arithmetic inside `.frame(width:`/`height:`; a numeric `width:` ≥ 300.

### LAY-04 — `position` / `offset` are not layout

`.position(x:y:)` and a static `.offset(...)` are forbidden for layout. They are allowed only as a transition/animation mechanism (animated displacement, `matchedGeometryEffect` and similar) with the reason recorded.

Absolute Figma coordinates are not a layout technique: they are valid at exactly one canvas size and make the screen impossible to re-lay-out.

Detection: any `.position(`; `.offset(` outside an animation context.

### LAY-05 — position with `alignment`, space with `padding`

```swift
.frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
```

`Spacer()` covers what `alignment` cannot express. Stacks plus `alignment`, `padding` and `spacing` cover static layout completely.

### LAY-06 — flexible frame initializers before fixed ones

Order of choice: no frame → `maxWidth/maxHeight` → `minWidth/idealWidth` → fixed `width/height` with a justification.

### LAY-07 — snap insets to system values, tolerance −2…+4pt

- A design value inside the asymmetric window **−2pt … +4pt** around the system value is replaced by the system value. The window applies to every edge, not only the horizontal one.
- The asymmetry is deliberate: growing an inset by up to 4pt is safe, shrinking it below the system value crowds the content, so only 2pt of shrink is allowed.
- Against the ≈16pt iOS default that window is 14–20pt: a uniform inset in that range on all sides → bare `.padding()`.
- A single axis → `.padding(.horizontal)` / `.padding(.vertical)`.
- Anything outside the window (below −2pt or above +4pt) → an explicit number from design context: `.padding(.top, 32)`.

The snap is a deliberate divergence from the mockup: it is recorded in the contract once, not re-litigated per screen. Stage 5 treats a divergence inside the −2…+4pt window and explained by this rule as a match, not a defect.

Detection: an inset literal in the 14–20 range is a candidate for the system value.

### LAY-08 — modifier order on a screen container

```swift
VStack { … }
    .padding()
    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
    .background(Color.red.ignoresSafeArea())
```

1. `.padding()` — content insets;
2. `.frame(maxWidth: .infinity, maxHeight: .infinity, alignment:)` — stretch and position;
3. `.background(...)` — a background takes the size of what it is attached to, so it comes **after** the stretch;
4. `.ignoresSafeArea()` — attach it to the **background**, otherwise the content also slides under the status bar and home indicator.

Equivalent form when there are several background layers:

```swift
ZStack {
    Color.red.ignoresSafeArea()

    VStack { … }
        .padding()
}
```

`.ignoresSafeArea()` on the outer container with content is allowed only when the content is deliberately meant to extend past the safe area; record the reason.

Detection: `.background(` before `.frame(maxWidth: .infinity` in one chain; `.ignoresSafeArea()` on a container that carries content.

### LAY-09 — no `scaleEffect` on text-bearing containers

The layer is rasterized and scaled as a whole: text is not re-laid-out at the final size, Dynamic Type is effectively disabled, and a non-integral factor adds blur. `scaleEffect` is for decorative graphics and animation, never as an adaptation mechanism.

### LAY-10 — geometry arithmetic requires a derivation

Any expression over `safeAreaInsets`, `geo.size` or a manual centering compensation carries the derivation in a comment and a record in the manifest. A tweak such as `.offset(y: -safeAreaInsets.top / 2)` without a derivation is forbidden.

Compensation is a symptom. Fix the cause first — where the geometry comes from and what the container is actually centered against — and introduce a compensation only if the cause cannot be removed, with the derivation written down.

### LAY-11 — prove adaptivity, do not claim it

- The stage 6 matrix must include the **smallest supported device** and devices **with and without a home indicator** (different bottom safe area) — these are different bug classes.
- A screen with geometry needs at least two `#Preview`s: the smallest and the largest supported device. The default preview is the reference device and proves nothing.
- Evidence is a screenshot per required device with explicit checks: the layout fits the screen, there is no unintended letterboxing, no clipped content, the background reaches the edges.

## 3. How this enters the stages

| Stage | What is added |
|-------|---------------|
| Preflight | A `Layout` row in the UI convention contract: reference canvas, permitted scaling API, smallest/largest device, patterns the project forbids |
| 1 (UI Plan) | Layout is described through containers and relations, not artboard coordinates; absolute coordinates from design context never move into the plan as a layout technique |
| 3 (implementation) | LAY-01…LAY-10 are part of the gate. A violation blocks the stage instead of becoming a stage 5 remark |
| 5 (comparison) | Compare on at least one **non-reference** size: at the reference size a fixed canvas matches pixel-for-pixel and hides the breakage. A divergence inside the −2…+4pt LAY-07 window is not a defect |
| 6 (adaptivity) | Matrix per LAY-11; evidence for every required device |
| 8 (review) | Re-run the detections for LAY-01…LAY-04, LAY-08, LAY-09 over the changed files |

LAY-01…LAY-04 and LAY-08…LAY-10 are detected by [`../scripts/ui_guard.py`](../scripts/ui_guard.py); pass `--reference-canvas` so LAY-01 keys on the project's actual artboard instead of a size threshold. LAY-05, LAY-06, LAY-07 and LAY-11 need intent, the project's system values or a screenshot — the script lists them as reviewer work and they stay part of the same gate. Waive a detected line in code with `// ui-guard: allow LAY-04 — <reason>`; the waiver is reported, not hidden, and is reviewed again at stage 8.

## 4. Failure catalog

Entry format: symptom → cause → rule → detection.

### FAIL-01 — perfect on the reference device, broken on a small one

- **Symptom:** pixel-perfect on iPhone 15 Pro; on an SE (375×667) there is side letterboxing, clipped content at the bottom and a visible vertical shift.
- **Cause:** a fixed `393×852` canvas plus an aspect-fit `scaleEffect`, with children positioned by absolute Figma coordinates (`.position(...)`), which makes the canvas inseparable from them.
- **Rule:** LAY-01, LAY-04.
- **Detection:** stage 3 — count `.position(` in the feature and `.frame(width:` with the reference size; stage 5 — a mandatory non-reference size.
- **Case:** `PetCare/Onboarding/OnboardingView.swift` plus `OnboardingPageLayers.swift` (≈40 `.position` calls), while `docs/architecture.md` explicitly marks the pattern as legacy and forbids it for new screens.

### FAIL-02 — legacy precedent beat a documented ban

- **Symptom:** a new screen reproduces a forbidden pattern "the way the neighbouring screens do it".
- **Cause:** the audit read code as convention; the documented rule was never searched for because the contract had no Layout area.
- **Rule:** §1 of this file — documentation outranks precedent; copying a legacy screen is prohibited.
- **Detection:** preflight — an unfilled `Layout` row blocks stages 1–8.

### FAIL-03 — magic safe-area compensation

- **Symptom:** the screen is centred correctly on a device without a home indicator and drifts upward on a device with one.
- **Cause:** `.offset(y: -safeAreaInsets.top / 2)` eyeballed from a single preview; the correct compensation for centring inside the reduced safe-area region is `-(top - bottom)/2`, which coincides only when `bottom == 0`.
- **Rule:** LAY-10, LAY-11.
- **Detection:** grep `safeAreaInsets` in the view layer without a derivation comment; a stage 6 matrix covering both device classes.

### FAIL-04 — the background did not fill the screen

- **Symptom:** `.background` shows as a patch the size of the content while the screen edges keep the system colour.
- **Cause:** `.background(...)` was applied before `.frame(maxWidth: .infinity, maxHeight: .infinity)`, so it took the content's ideal size; the following frame merely centred an already-painted view.
- **Rule:** LAY-08.
- **Detection:** `.background(` before `.frame(maxWidth: .infinity` in one chain.
