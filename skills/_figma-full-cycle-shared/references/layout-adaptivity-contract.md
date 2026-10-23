# Layout & Adaptivity Contract

The sixth area of the project UI convention contract. The goal is to fix **which layout API** the feature is built with, so the screen adapts to every supported size by itself instead of being tuned with numbers for one device.

**Read it in full at the start of stage 3** — the stage that enforces LAY-01…LAY-13 — and keep it in session for stages 5, 6 and 8. The preflight audit does not read this file: it resolves the `Layout` row from the baseline digest in [`project-ui-conventions.md`](project-ui-conventions.md), and reads this contract early only when that row cannot be resolved without it.

The area resolves with the same statuses as the others: `matched / project-specific / skill-fallback / inferred-from-code / conflict / not-applicable`.

Standalone validators use [validation-context.md](validation-context.md) for report destinations
and scope. Without design evidence, reference-canvas fields are `not-applicable`; screen bounds,
supported configurations and intended edge relations still require evidence.

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

Detection: a `.scaleEffect(` with a **static** factor paired with a frame pinning **both** dimensions **in the same type body**, where that frame is not provably smaller than the screen. One readable side settles it — a screen is large in both dimensions, so a frame 280pt tall on an 852pt canvas is content whatever its width does. Press feedback (`isPressed ? 0.97 : 1`) is the animation case — and so is any factor driven by state, in the sense LAY-09 spells out — a frame belonging to a different type is a different screen, and a size taken from live geometry (`proxy.size.width` inside a `GeometryReader`) is not a pinned size at all — it means "fill the parent", the opposite of an artboard. The frame reported is the one directly above the `scaleEffect`, because that is the one being scaled. The size does not have to be a literal — a named constant is the same canvas, and `.frame(width: OnboardingLayout.width, height: OnboardingLayout.height)`, resolving through `CGSize(width: 393, height: 852)` in another file, is the exact shape this rule was written from. `<shared-root>/scripts/ui_guard.py` resolves constants across every file in the run, covering literals, one-line enums, multi-line declarations, computed properties, `as` casts, any `Type(width:height:)` one constant naming another, and a `typealias` standing in for a type. What it cannot resolve counts as the screen, so an unfamiliar form costs a false positive rather than a silent miss — and `ui_guard.py constants` prints what it read, which is how to tell those two apart in one command.

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

**Exception — a fixed-size composition.** A group of elements that form one piece of artwork, sized in the design and anchored natively by its parent, places its parts against *each other*, not against the screen. That is the same allowance LAY-03 already makes for a genuinely fixed element, applied to a group. Three animals inside a 280×180 illustration are artwork; the screen they sit on is not.

Declare it once, above the block:

```swift
// ui-guard: composition OnboardingAnimals — 280×180 artwork, anchored by the parent
ZStack {
    Image("cat").offset(x: -84.1, y: 0.4)
    …
}
.frame(width: 280, height: 180)
```

The marker covers the block, the modifiers chained onto it — including the frame that declares the block's size — and suspends the fixed-geometry rules **LAY-02, LAY-03 and LAY-04** inside it. Fixed geometry is what artwork is made of; flagging an illustration for declaring its own dimensions is the same mistake as flagging its internal offsets. One comment for the group, not a waiver per element: a rule that costs a waiver per element teaches people to waive without reading.

Two conditions, both checked:

- **The group is anchored natively.** Its own placement obeys LAY-04 and LAY-05; only its interior is exempt.
- **The group is not the screen.** A composition is refused unless its frame is *provably smaller* than the screen — smaller than 90% of the reference canvas in at least one dimension, or under 300pt in both when no canvas was given. A size the guard cannot resolve counts as the screen, so an unreadable value is never an escape. Otherwise the marker would license exactly the fixed-canvas pattern LAY-01 forbids, one comment at a time.

"Provably" is doing real work in that sentence. The first implementation compared against a flat 300pt threshold, which refused a 381×373 illustration on a 393pt canvas while accepting a genuine 393×852 canvas whose size was written as `CGSize(width:height:)` — wrong in both directions at once.

Every composition is listed in the guard's output, including one that exempted nothing: an exemption nobody sees is a rule nobody enforces, and a marker that silently matches nothing rots in the source.

Detection: any `.position(`; any `.offset(` outside an explicit animation/transition/gesture context, minus declared compositions. A computed property, environment geometry helper or named `…Compensation` is still static layout; naming it or exposing it through a runtime wrapper must never hide it.

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

Detection: a `.scaleEffect(` whose factor is **static** — a literal, a constant or a plain symbol — in a file carrying `Text`. A factor driven by state is the animation case this rule permits and is not a finding, and state arrives in two shapes, both of which count:

- **Announced by the expression** — a ternary, a comparison or an animation flag: `configuration.isPressed ? 0.97 : 1`, press feedback in a `ButtonStyle` being the common shape.
- **Reached through a declaration** — the factor reads a property the runtime rewrites (`@State`, `@Binding`, `@GestureState`, an observed store), directly or through however many computed properties stand between. `.scaleEffect(1 - avatarProgress * 0.2)`, where `avatarProgress` derives from an `@State` scroll offset, is a collapsing header: a value that changes on every frame of a scroll, written as plain arithmetic with no keyword to say so. Reading only the first shape reports every one of them.

A symbol that is never declared as state stays static, so the rule keeps failing closed: geometry is not state, and `min(w / 393, h / 852)` over text is the artboard fit this rule and LAY-01 are written from.

### LAY-10 — geometry arithmetic requires a derivation

Any expression over `safeAreaInsets`, `geo.size` or a manual centering compensation carries the derivation in a comment and a record in the manifest. A tweak such as `.offset(y: -safeAreaInsets.top / 2)` without a derivation is forbidden.

Compensation is a symptom. Fix the cause first — where the geometry comes from and what the container is actually centered against — and introduce a compensation only if the cause cannot be removed, with the derivation written down.

### LAY-11 — prove adaptivity, do not claim it

- The required adaptivity matrix includes the **smallest and largest supported devices** and
  devices **with and without a home indicator** (different bottom safe area). Every required
  target needs a native capture; a Preview alone does not satisfy device screenshot coverage.
- A screen with geometry needs at least two `#Preview`s: the smallest and the largest supported device. The default preview is the reference device and proves nothing.
- Evidence is a screenshot per required device with explicit checks: the layout fits the screen, there is no unintended letterboxing, no clipped content, the background reaches the edges.
- The UI Plan, or standalone report, records relational edge invariants. Intended equal left/right/bottom insets are verified on the smallest and largest device within 1pt or equivalent screenshot-pixel tolerance, and on the non-reference size during design comparison; “nothing clips” does not prove centring.
- When a real mock and `sips` exist, [`../scripts/screenshot_diff.py`](../scripts/screenshot_diff.py) answers three checks mechanically — letterboxing, pillarboxing, background to the edges. Without either, inspect every native capture against screen bounds and project invariants; no fabricated mock or mechanical clean marker. The reference/no-reference execution paths belong to `swiftui-adaptivity-check`.
- **Clipping it cannot gate across device classes.** Normalizing stretches the mock, while a native layout adapts by holding its metrics in points, so a correctly adapted screen differs in the bottom band exactly as a broken one does. Beyond the aspect tolerance the script reports that number and refuses to decide on it. On the smallest supported device, clipping is confirmed by eye.
- It is a filter, not the gate — also blind to typeface, icon shape, copy and small colour shifts. Eyes go on every failing row, one passing row per screen, and the smallest-device row.

### LAY-12 — the system owns the screen and presentation shape

Do not copy the corner radius of a Figma device frame into the root screen. A full-screen view, sheet or cover fills the region the system gives it; the physical display, window and presentation controller apply whatever clipping their device or presentation requires. A rectangular device must therefore stay rectangular without app code removing its corners.

Rounded app-owned surfaces — cards, panels, buttons and an explicitly specified custom container — remain valid. The distinction is ownership, not radius size: a screen-sized `.clipShape(RoundedRectangle(...))`, `.cornerRadius(...)` or equivalent mask is forbidden unless the project contract explicitly says the app owns that outer shape.

Detection: a rounded clip/corner modifier on a chain that pins both screen dimensions or stretches to both `.infinity` axes.

### LAY-13 — overflow artwork must not size the screen stack

An oversized decorative child has an ideal size. If it participates directly in a screen-level `ZStack`, that ideal width or height can become the stack's layout width before an outer frame is applied; the outer frame then centres the oversized stack and shifts all ordinary content. A fixed frame on the root does not undo that measurement.

Artwork that extends beyond the screen uses one of these shapes:

- place it in `.background` / `.overlay`, where it cannot propose the foreground stack's size; or
- locally bound the artwork to the live screen region, with the bounding `.frame(...)` followed by `.clipped()` / an intentional mask, before it enters the parent stack.

Negative padding and artwork-local transforms may create visual overflow only inside that bounded layer. They must not be used as a compensation on the screen container. When the artwork exceeds the reference canvas, pass `--reference-canvas`; `ui_guard` reports an image without a later screen bound and clip.

Detection: `Image` / `AsyncImage` with a resolvable dimension larger than the reference canvas and no later screen-sized bound plus clip in the same modifier chain. Unresolved overflow remains reviewer work: inspect decorative children of every screen-level stack.

## 3. How this enters the stages

| Stage | What is added |
|-------|---------------|
| Preflight | A `Layout` row in the UI convention contract: reference canvas, permitted scaling API, smallest/largest device, patterns the project forbids |
| 1 (UI Plan) | Layout is described through containers and relations, not artboard coordinates; absolute coordinates from design context never move into the plan as a layout technique |
| 3 (implementation) | LAY-01…LAY-13 are part of the gate. A violation blocks the stage instead of becoming a stage 5 remark |
| 5 (comparison) | Compare on at least one **non-reference** size: at the reference size a fixed canvas matches pixel-for-pixel and hides the breakage. A divergence inside the −2…+4pt LAY-07 window is not a defect |
| 6 (adaptivity) | Matrix per LAY-11; evidence for every required device |
| 8 (review) | Re-run the detections for LAY-01…LAY-04, LAY-08…LAY-10, LAY-12 and LAY-13 over the changed files |

LAY-01…LAY-04, LAY-08…LAY-10, LAY-12 and LAY-13 are detected by [`../scripts/ui_guard.py`](../scripts/ui_guard.py); pass `--reference-canvas` so LAY-01 and LAY-13 key on the project's actual artboard instead of a size threshold. LAY-05, LAY-06, LAY-07 and LAY-11 need intent, the project's system values or a screenshot — the script lists them as reviewer work and they stay part of the same gate. Waive a detected line in code with `// ui-guard: allow LAY-04 — <reason>`; the waiver is reported, not hidden, and is reviewed again at stage 8.

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

### FAIL-05 — decoration shifted every foreground element on a compact device

- **Symptom:** foreground content is centred on the reference device but moves left or right on a narrower device, while its own paddings look correct in source.
- **Cause:** artwork wider than the screen participated in the root `ZStack` measurement; the outer screen frame centred the oversized stack rather than bounding the artwork locally.
- **Rule:** LAY-13, LAY-11.
- **Detection:** stage 3 — LAY-13 with `--reference-canvas`; reviewer inspection for unresolved decorative sizes. Stage 6 — verify equal edge insets on the smallest device, not clipping alone.

### FAIL-06 — the app rounded a rectangular device

- **Symptom:** a full-screen background has visible white cut-outs in the corners on an SE-class rectangular display, although the rounded mock looked correct on the reference device.
- **Cause:** the Figma device-frame radius was implemented as a root `.clipShape` / `.cornerRadius` instead of being treated as presentation chrome.
- **Rule:** LAY-12.
- **Detection:** stage 3 — a rounded clip on a screen-sized chain; stage 5/6 — confirm the root reaches every system-provided corner and has no app-owned device mask.
