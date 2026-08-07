# Colors Contract

The Colors area of the project UI convention contract. The goal is to fix **where a color value lives, what names it**, and **what a view is allowed to reference**, so a feature does not quietly grow a second palette.

**Read it in full at the start of stage 3** — the stage that enforces COL-01…COL-09 — and keep it in session for stages 5 and 8. The preflight audit does not read this file: it resolves the `Colors` row from the baseline digest in [`project-ui-conventions.md`](project-ui-conventions.md), and reads this contract early only when that row cannot be resolved without it.

The area resolves with the same statuses as the others: `matched / project-specific / skill-fallback / inferred-from-code / conflict / not-applicable`.

## 1. What to resolve from the project

Search by terms as well as section names: `Color`, `palette`, `token`, `colorset`, `Assets.xcassets`, `appearance`, `dark mode`, `tint`, `accent`, `theme`, `semantic`, `hex`, `generated symbols`, `ASSETCATALOG_COMPILER_GENERATE_SWIFT_ASSET_SYMBOL_EXTENSIONS`.

Record in the manifest:

- the **palette mechanism**: where raw values live (asset catalog, token file, generated accessors) and how a symbol reaches code;
- the **palette naming scheme**: entries named by value (`hexD7D7D7`) or by role (`surfaceSubtle`) — whichever the project uses, applied to the whole catalog;
- the **semantic layer**: where role tokens live (`<Feature>Style.swift`, a design-system module, a theme struct) and what a view may reference;
- system/brand slots that are not palette entries (accent color, tint, system backgrounds);
- appearance variants in use (light/dark, high contrast) and how a variant pair is named;
- the project's color guard, if one exists (a script, a lint rule, a test) and its exact invocation;
- where literals are explicitly permitted, if anywhere (previews, tests, dev diagnostics).

## 2. Baseline rules

The baseline applies unless the project defines a more specific compatible rule.

### COL-01 — two layers, and a view sees only the semantic one

The palette holds the raw value. The semantic layer holds the role. A view references the role, never the palette entry:

```swift
// palette:   Colors/hexDB69FF.colorset      → Color.hexDB69FF
// semantics: enum TabBarPalette { static let activeIndicator = Color.hexDB69FF }
// view:      .foregroundStyle(TabBarPalette.activeIndicator)
```

A project that already names palette entries by role still keeps the split: a view referencing the palette directly is what makes a color impossible to re-point later.

Detection: a palette symbol referenced outside the files that own the semantic layer.

### COL-02 — one value, one palette entry

Before adding a color, search the palette **by value**, not by name. An existing entry with the same value is reused; a second entry for the same value is a duplicate and gets merged.

Duplicates are how one color ends up re-added per feature, and how a later "change this color" edit silently misses half the screens.

Detection: two palette entries whose components are equal.

### COL-03 — one naming scheme for the whole palette

The project decides whether palette entries are named by value or by role. That choice applies to the whole catalog. Mixing the two schemes is a `conflict`, not a style preference: with a mixed catalog neither "does this color already exist?" nor "what is this color for?" can be answered without reading every entry.

Whatever the scheme, the name must not encode the usage site of one feature (`onboardingTopBackground`) unless the project's documented scheme is exactly that — such a name lies the moment the color is reused elsewhere.

### COL-04 — alpha never belongs in the name

Transparency is applied in code (`.opacity(0.16)`) over the base entry. A separate palette entry per alpha level is forbidden: it multiplies the catalog and hides that the two entries are the same color.

Detection: palette entry names carrying an opacity/alpha suffix; entries whose components differ only in alpha.

### COL-05 — no inline color literals, in any form

Forbidden in product code: `Color(red:green:blue:)`, `Color(white:)`, `Color(hue:saturation:brightness:)`, `Color(hex:)` and equivalents, `UIColor(red:…)`/`NSColor(...)`, `#colorLiteral`, and raw hex strings passed to a color initializer.

Literals are acceptable only where the project explicitly allows them (previews, tests, dev diagnostics) and only through a recorded allowlist.

Detection must enumerate every form. A guard that matches only two of them reports "0 violations" while a third form spreads — see FAIL-02.

### COL-06 — exact values come from design context

Take the value from design context or Figma variables, never with an eyedropper on a screenshot: a screenshot carries blend, opacity and export color-space error.

When the exact Figma value conflicts with an existing semantic token, prefer the resolved project convention and record the expected visual difference for stage 5.

### COL-07 — never collapse appearance variants

Existing light/dark and other appearance variants are preserved. New high-contrast or accessibility variants are added only when project documentation or the resolved Accessibility contract requires them.

How a variant pair is named and stored is project-resolved. A palette with no dark appearance yet is not permission to hard-code a light value in a view.

### COL-08 — system and brand slots stay slots

An accent/tint/system slot (`AccentColor` and equivalents) is read through its system accessor and is not duplicated as an ordinary palette entry. A duplicate makes two sources of truth for one brand color.

### COL-09 — a missing token is a contract question, not an improvisation

A new palette entry or semantic token is added only through the project's existing mechanism. If the needed token does not exist and cannot be added that way, record `conflict` and ask before stage 3. Never introduce a second color system inside a feature.

### COL-10 — the gate is a real detection run

- The project has a color guard (script, lint rule, test) → it is the gate, run with its exact documented invocation, evidence recorded.
- No project guard → [`../scripts/ui_guard.py`](../scripts/ui_guard.py) is the shipped detection for COL-01, COL-02, COL-04 and COL-05 over the feature's changed files. COL-01 needs `--palette-symbol` and `--semantic-layer` from the resolved contract; COL-02 and COL-04 need `--asset-catalog`. Without those flags those rules do not run — the coverage note says so, and an unflagged run is not a clean palette.
- Either way the run happens at stage 3 and again at stage 8, and "clean" means a recorded command with its output, not an assertion.
- COL-03 and COL-06…COL-09 are not machine-checkable and are never covered by any guard's clean run — they are reviewer work at the same two gates. Before trusting a **project** guard, check its pattern against the full COL-05 form list; a form it cannot match goes into the manifest as a known gap (FAIL-02).

## 3. How this enters the stages

| Stage | What is added |
|-------|---------------|
| Preflight | The `Colors` contract row: palette mechanism and naming scheme, semantic layer location, system slots, appearance variants, project guard invocation, literal allowlist |
| 1 (UI Plan) | Color mappings point at semantic tokens with provenance; a value with no token becomes an explicit `tbd`, never an inline value |
| 3 (implementation) | COL-01…COL-09 are part of the gate; the guard or the detections run over the changed files |
| 5 (comparison) | Verify color numbers from design context, not by sampling pixels; deviations mandated by the resolved contract are recorded, not "fixed" into literals |
| 8 (review) | Re-run the guard or the detections over the changed files |

## 4. Failure catalog

Entry format: symptom → cause → rule → detection.

### FAIL-01 — the palette is named after one usage site

- **Symptom:** the same color exists several times under per-feature names; a name like `onboardingTopBackground` turns out to be used in 14 files, only one of which belongs to Onboarding.
- **Cause:** palette entries named after where they were first used, so every new feature adds its own entry instead of finding the existing value.
- **Rule:** COL-01, COL-02, COL-03.
- **Detection:** palette entries with equal components; palette symbols referenced far outside the feature their name claims.

### FAIL-02 — the guard's regex covered only part of the literal forms

- **Symptom:** the color guard reports zero violations while a literal form keeps spreading through the code.
- **Cause:** the detection matched `Color(red:` and `Color(white:` only, so `Color(hue:saturation:brightness:)` was invisible to it.
- **Rule:** COL-05, COL-10.
- **Detection:** review the guard's pattern against the full list of forbidden forms before trusting its clean run; a form that cannot be matched goes into the manifest as a known gap.

### FAIL-03 — two project documents disagree about the policy

- **Symptom:** the architecture document still recommends the naming scheme a dedicated colors document has already replaced; an agent that reads only the first one violates the second.
- **Cause:** a policy migration updated the specialized document and left the general one stale.
- **Rule:** the audit records `conflict` and asks; picking the more recent or more specific document silently is forbidden (see `project-ui-conventions.md` §3).
- **Detection:** during the audit, reconcile every source found for the area against the others instead of stopping at the first hit.

### FAIL-04 — alpha variants as separate palette entries

- **Symptom:** the catalog carries several entries of the same color at different opacities.
- **Cause:** the mockup exposed a translucent fill and it was imported as its own color.
- **Rule:** COL-04.
- **Detection:** entries whose components differ only in alpha; opacity-suffixed entry names.
