# Figma Full Cycle

[English](README.md) | [Russian](README.ru.md) | [Simplified Chinese](README.zh-CN.md) | [Hindi](README.hi.md) | [Spanish](README.es.md) | [French](README.fr.md) | [Arabic](README.ar.md) | [German](README.de.md) | [Korean](README.ko.md)

**Ein übergeordneter Figma-Frame als Eingabe. Ein geprüftes, gebautes und konventionskonformes Feature als Ergebnis.**

`figma-full-cycle` ist ein orchestrierender [Agent Skill](https://code.claude.com/docs/en/skills) für
Claude Code und Codex. Du übergibst den Link zum übergeordneten Frame eines Features in Figma; der Skill
steuert den gesamten Weg vom Design bis zum gemergten Code — Spezifikation, Assets, UI, Designvergleich,
Anpassungsfähigkeit, Logik und Review — in acht Stufen mit Freigabeprüfungen, einem Commit pro Stufe
und einem versionierten Manifest als verbindlicher Referenz.

[![Lizenz: MIT](https://img.shields.io/badge/License-MIT-black.svg)](LICENSE)
[![CI](https://github.com/gwair1989/figma-full-cycle/actions/workflows/ci.yml/badge.svg)](https://github.com/gwair1989/figma-full-cycle/actions/workflows/ci.yml)
![Skills: 6](https://img.shields.io/badge/skills-6-blue)
![Laufzeitabhängigkeiten: keine](https://img.shields.io/badge/runtime%20deps-none-brightgreen)
![Ziel-UI: SwiftUI](https://img.shields.io/badge/target-SwiftUI-orange)

> **Hinweis zur Sprache.** Skills, Beschreibungen, Agentenmetadaten, Referenzen, Vorlagen und
> Repository-Dokumentation sind auf Englisch verfasst; lokalisierte `README.*.md`-Dateien bilden die
> Ausnahme. [README.md](README.md) ist die Quelle für README-Übersetzungen. Dokumente, die die Skills
> in dein Projekt schreiben, folgen **deiner** Sprache. Maschinenlesbare Strukturen — Schlüssel im
> UI Plan, Statuswerte, Manifestüberschriften und Commit-Betreffzeilen — bleiben auf Englisch,
> damit Validierung und Fortsetzung weiterhin funktionieren.

---

## Ein Plugin, sechs Einstiegspunkte

Dieses Repository ist sowohl eine Sammlung wiederverwendbarer Skills als auch ein verteilbares
Codex-Plugin. Nach der Installation sind alle sechs Workflows verfügbar; der Aufruf eines Workflows startet die anderen nicht.

| Skill | Eigenständig verwenden für |
|---|---|
| `figma-full-cycle` | Umsetzung eines vollständigen Figma-Features; orchestriert die Skills für Spezifikation, Assets, Vergleich und Anpassungsfähigkeit |
| `figma-feature-spec` | Erstellung einer Feature-Spezifikation ohne Implementierung der App |
| `import-figma-assets` | Import von Grafiken in einen Xcode-Asset-Katalog |
| `figma-design-compare` | Vergleich bestehender Screens mit einem festgelegten Figma-Design |
| `swiftui-adaptivity-check` | Prüfung unterstützter Konfigurationen, mit oder ohne Figma |
| `device-usage` | Tests auf einem physischen iPhone über Device Hub, ohne Figma oder Pipeline |

Dies ist das maßgebliche Repository für alle sechs Skills. Entwicklung, Issues und Releases von
Device Usage finden jetzt hier statt; das frühere eigenständige Repository wurde entfernt.
`device-usage` lässt sich weiterhin separat installieren und aufrufen.

Device Hub ist der primäre Kanal für den Workflow mit physischen Geräten; iPhone Mirroring dient als
Ausweichlösung. Das Plugin liefert Anweisungen und einen optionalen Screenshot-Recorder. Es installiert
weder Xcode noch Computer Use, einen MCP-Server oder macOS-Berechtigungen. Simulatorprüfungen bleiben
separat; ein angeschlossenes Telefon ersetzt nicht die Testmatrix für die Anpassungsfähigkeit.
Prüfungen auf physischen Geräten werden nur dann in den vollständigen Zyklus aufgenommen, wenn der
Nutzer oder das Projekt sie verlangt.

## Warum es diesen Skill gibt

Ein einzelner Prompt wie „Implementiere diesen Figma-Screen“ scheitert bei echten Features auf vorhersehbare Weise:

| Problem | Was der Skill stattdessen tut |
|---|---|
| Der Agent erfindet Produktverhalten, das im statischen Mockup nie enthalten war | Jede Unbekannte wird zu einer protokollierten Frage oder einem ausdrücklichen `TBD` — nie zu einer stillschweigenden Vermutung |
| Der Agent ignoriert die projektspezifischen Konventionen für Strings, Typografie und Farben | Rein lesende Prüfung der Konventionen **vor** Figma und vor jeder Änderung; fünf geklärte Vertragszeilen sind Voraussetzung für jede Stufe |
| Vollständige Lokalisierungskataloge und rohe MCP-Payloads verbrauchen das Kontextfenster | Begrenzte, rein lesende Hilfsprogramme, gezielte Figma-Abfragen, Delegation an Subagenten und kompakte Nachweise im Zustand |
| Ein riesiger Commit, der sich nicht sinnvoll prüfen lässt | Eine Stufe = ein Commit, jeweils erst nach einer durch einen echten Befehl belegten Freigabeprüfung |
| „Alles grün“ wird behauptet, ohne etwas auszuführen | Freigabeprüfungen verlangen Nachweise: Befehl, Zeitpunkt, Exit-Code und Artefaktpfad |
| Die Designumsetzung hinterlässt uncommittete Änderungen im Hauptbranch | Das Feature läuft in einem eigenen Branch samt Worktree; Aufräumen erst nach bestätigtem Merge |

## Die Pipeline

| # | Stufe | Freigabeprüfung (gekürzt) |
|---|---|---|
| 0 | Worktree — Branch, Secrets per Symlink, Build-Standardwerte, Ausgangs-Build und -Tests | Ausgangszustand dokumentiert, Manifest erstellt |
| 1 | Spezifikation + UI Plan — Screens, Navigationsplan, Asset-Inventar, Textinventar | Spezifikation und `UI_PLAN.json` auf Datenträger, `ui_plan.py --phase ui` erfolgreich, blockierende Fragen beantwortet |
| 2 | Assets — Import anhand des node-id-Inventars | Build erfolgreich, Vorhandensein jedes Assets bestätigt |
| 3 | UI-Implementierung + Grundgerüst der Projektarchitektur | Nachweise zum UI Plan aktuell, Strings geprüft, Build erfolgreich, jeder Screen und Zustand umgesetzt |
| 4 | UI-Refactoring — *bedingt*, nur bei Befunden | Build erfolgreich, betroffene Prüfungen als `stale` markiert |
| 5 | Designvergleich — Vergleich jedes Screens mit dem festgelegten Figma-Frame | Bericht auf Datenträger, Abweichungen behoben und erneut geprüft |
| 6 | Anpassungsfähigkeit — kleine/große Screens, Hell-/Dunkelmodus, Inhaltsgrößen, Gebietsschemata, Tastatur | Keine abgeschnittenen Inhalte oder Überlappungen, Nachweise gespeichert |
| 7 | Geschäftslogik + Laufzeitnavigation + Tests | `ui_plan.py --phase production` erfolgreich, Tests bestanden, TBDs gekennzeichnet |
| 8 | Abschließendes Review | Review ohne offene Befunde, keine verbliebenen nutzerseitig sichtbaren Literale, sauberer Zwischenstand committet |

Zwei Eigenschaften machen das in der Praxis handhabbar:

- **Ab jeder Stufe fortsetzen.** Der Zustand liegt auf dem Datenträger und wird mit git abgeglichen — `start: stage N`,
  oder bitte einfach darum, das Feature fortzusetzen.
- **`ui-first`-Modus.** Das Design existiert, die Spezifikation noch nicht? Die Stufen 0–6 laufen sofort;
  Produktfragen werden als `deferred-to-spec` erfasst, statt zu blockieren; die Stufen 7–8 warten auf die Anforderungen.

## Voraussetzungen

- **Agent:** Claude Code oder Codex (ein Adapter ordnet jede Fähigkeit konkreten Toolnamen zu).
- **Figma MCP** mit Lesezugriff sowie `FIGMA_ACCESS_TOKEN` spätestens ab Stufe 5.
- **Python 3.9+** — nur die Standardbibliothek, keine Installation per `pip install` nötig.
- **Zielprojekt:** eine Xcode-/SwiftUI-App. Die Architektur ergibt sich aus der Projektdokumentation
  oder einer ausdrücklichen Nutzerentscheidung. Fehlende, mehrdeutige oder widersprüchliche Dokumentation
  → den Nutzer fragen; Quellcode und installierte Skills bestimmen die Architektur nicht. Die Entscheidung
  und ihre Quelle werden vor der Implementierung im Manifest und in der Spezifikation festgehalten, auch
  bei `ui-first`. Die Stufen 3 und 7 folgen dieser Architektur; ein bestimmtes Architektur-Framework ist nicht erforderlich.
- **Begleitende Skills** werden **ermittelt, nicht unter einem bestimmten Namen vorausgesetzt.** Die
  Vorabprüfung durchsucht die tatsächlich auf deinem Rechner installierten Skills, MCP-Tools,
  MCP-Ressourcen, Plugins und projektlokalen Skripte und ordnet jeder *Rolle* einer Stufe eines davon zu —
  `design-to-code-workflow`, `platform-ui-idiom`, `app-architecture`, `visual-comparison`, `code-review`, …
  Umbenannte Skills, Skills mit Namespace oder Plugin-Präfix und ganz neue Anbieter-Skills werden auf
  dieselbe Weise erkannt; findet sich für eine Rolle nichts, greift ein dokumentierter Ersatzweg.
  Nur die hier mitgelieferten Skills sind namentlich festgelegt: `figma-full-cycle`, `figma-feature-spec`,
  `import-figma-assets`, `figma-design-compare`, `swiftui-adaptivity-check` und optional `device-usage`.
  Die mitgelieferten Identitäten werden zu ihren tatsächlich registrierten Namen aufgelöst, einschließlich Plugin-Namespaces.
- **Nur für Prüfungen auf physischen iPhones:** macOS, ein gekoppeltes physisches iPhone, Xcode mit
  Device Hub und ein kompatibles Desktop-Tool für Computer Use für autonome GUI-Aktionen. Befolge die
  Fähigkeitsprüfungen des mitgelieferten Skills; CLI-Diagnosen bleiben möglich, wenn keine GUI-Steuerung verfügbar ist.
- **Optionaler Recorder für Gerätenachweise und dessen Tests:** Node.js 22+, nur die Standardbibliothek.

Fehlende Fähigkeiten werden vorab in einer einzigen Liste von Blockaden gemeldet, statt erst mitten
im Build einzeln aufzufallen. Die ermittelten Zuordnungen werden zusammen mit der Prüfung der
Figma-Authentifizierung und der Erreichbarkeit der Knoten im Fähigkeitenverzeichnis des Manifests gespeichert.

## Installation

### Codex-Plugin

Das portable Manifest ist `plugin.json`; `.codex-plugin/plugin.json` sorgt für Codex-Kompatibilität.
Der Repository-Marktplatz ist `.agents/plugins/marketplace.json`. Führe aus diesem Checkout mit einer
Codex-CLI, die `plugin add` anbietet, Folgendes aus:

```bash
git clone https://github.com/gwair1989/figma-full-cycle.git
cd figma-full-cycle
codex plugin marketplace add .
codex plugin add figma-full-cycle@figma-full-cycle-local
```

Alternativ kannst du den lokalen Marktplatz im Plugins Directory der Desktop-App auswählen. Starte
nach der Installation eine neue Sitzung und wähle den Skill unter dem genauen Namen aus seinem
Katalog aus; ein Plugin kann einen qualifizierten Namen verwenden, etwa `figma-full-cycle:device-usage`.
Die Paketierung folgt dem [offiziellen Plugin-Format](https://developers.openai.com/plugins/build/plugins).
Dieses Repository ist eine lokale Distributionsquelle, kein Eintrag in einem öffentlichen Verzeichnis.

### Eigenständige Skills

```bash
git clone https://github.com/gwair1989/figma-full-cycle.git
cd figma-full-cycle
./install.sh
```

`install.sh` legt für alle sechs Skills Symlinks in `~/.claude/skills` an — dadurch aktualisiert `git pull` sie direkt.

```bash
./install.sh --target ~/.codex/skills   # Codex
./install.sh --target ~/.agents/skills --skill device-usage   # nur der Device-Hub-Workflow
./install.sh --target ~/.agents/skills --skill figma-feature-spec --skill import-figma-assets
./install.sh --target .claude/skills    # nur dieses Projekt
./install.sh --copy                     # kopieren statt Symlinks anlegen
./install.sh --force                    # vorhandenen Skill gleichen Namens ersetzen
./install.sh --uninstall                # die hiermit installierten Skills entfernen
```

`--skill` kann mehrfach angegeben werden. Die Auswahl von `figma-full-cycle` installiert auch dessen vier Begleiter:
`figma-feature-spec`, `import-figma-assets`, `figma-design-compare`, `swiftui-adaptivity-check`.
Device Usage bleibt optional. Der vollständige Zyklus sowie jeder der beiden visuellen Validatoren
installieren `_figma-full-cycle-shared/` einmal neben den Skill-Verzeichnissen. Es enthält verbindliche
Verträge und rein lesende Hilfsprogramme, besitzt keine `SKILL.md` und ist kein weiterer Einstiegspunkt.

```bash
./install.sh --target ~/.codex/skills --copy --skill figma-design-compare
./install.sh --target ~/.codex/skills --copy --skill swiftui-adaptivity-check
```

Kopierte visuelle Skills werden zusammen mit dem benachbarten Verzeichnis `_figma-full-cycle-shared/`
weitergegeben; der ursprüngliche Checkout und der Full-Cycle-Skill sind nicht nötig. Verwende `--force`,
um eine vorhandene kopierte Installation zu aktualisieren. Die Deinstallation entfernt nur die
ausgewählten Symlinks und behält Begleiter sowie gemeinsame Ressourcen bei, damit andere Nutzer dieser
Ressourcen weiter funktionieren; kopierte Verzeichnisse müssen manuell entfernt werden. Der Quellbaum
lässt sich auch direkt als Plugin verwenden und enthält dabei das gemeinsame Verzeichnis.

Verwende für jeden Skill entweder die Plugin-Installation oder die eigenständige Registrierung.
Eigenständige Aufrufe in Codex verwenden `$<skill-name>`, darunter `$figma-design-compare` und
`$swiftui-adaptivity-check`. Dieselben Verzeichnisse funktionieren in Claude Code; Device Hub benötigt
weiterhin Computer Use auf dem Desktop.

Liegen diese Skills bereits in deinem Skill-Verzeichnis? `--force` ersetzt sie und verschiebt die
alten Kopien nach `.skill-backups` **neben** dem Skill-Verzeichnis — niemals hinein, wo ein Agent
die Sicherung als zweiten, doppelten Skill erkennen würde.

Überprüfung: Starte eine neue Agentensitzung und prüfe, ob `figma-full-cycle` in der Skill-Liste erscheint.

## Verwendung

Gib dem Skill den Link zum **übergeordneten** Frame — dem Container, der alle Screens des Ablaufs
enthält, nicht nur einen einzelnen Screen:

```text
Vollständiger Zyklus ab diesem Figma-Frame: https://figma.com/design/<fileKey>/App?node-id=1234-5678
```

```text
Implementiere das Feature aus <url>, mode: ui-first — die Anforderungen folgen später
```

```text
Setze <FEATURE> fort, start: stage 5
```

Du kannst Anfragen in deiner Sprache stellen; erzeugte Projektdokumente folgen dieser Sprache.
Eine lokalisierte README findest du über die Sprachlinks oben.

### Eigenständige visuelle Prüfungen

```text
Verwende $figma-design-compare, um diese implementierten Screens mit <Figma URL> zu vergleichen; speichere einen Bericht.
Verwende $swiftui-adaptivity-check, um diese Screens auf unterstützten Geräten und mit verschiedenen Textgrößen zu prüfen, ohne Figma.
```

Eigenständige Prüfungen schreiben `docs/<RUN>_DESIGN_COMPARE.md` oder `docs/<RUN>_ADAPTIVITY.md` und
legen lokale Artefakte unter `docs/.cache/<RUN>/` ab. Sie benötigen weder ein Pipeline-Manifest noch
einen UI Plan, erstellen keine Commits und wenden Korrekturen nur mit Autorisierung an. Für einen
eigenständigen Vergleich genügen authentifizierte MCP-Lesezugriffe; der vollständige Zyklus behält
seine eigene Prüfung der Zugangsdaten in Stufe 5 bei. Die Prüfung der Anpassungsfähigkeit benötigt
weder Figma-URL noch Token oder Mockup; ohne Mockup oder `sips` wird jede native Aufnahme direkt
begutachtet. Die Stufen 5/6 rufen dieselben Skills mit Pipeline-Kontext auf und importieren Bericht
und Nachweise in das vom Orchestrator verwaltete Manifest.

### Was in dein Projekt geschrieben wird

| Datei | Versioniert | Rolle |
|---|---|---|
| `docs/<FEATURE>_PIPELINE.md` | ja | Manifest: Stufen, Freigabeprüfungen, Nachweise, Fragenprotokoll, Entscheidungen |
| `docs/<FEATURE>_UI_PLAN.json` | ja | Maschinell geprüfter Übergabevertrag von der Spezifikation zur Implementierung |
| `docs/<FEATURE>_PIPELINE.local.md` | nein (per gitignore ausgeschlossen) | Lokale Laufzeitdaten: absolute Pfade, Simulator-UDID |

## Lieferumfang

```
skills/
├── _figma-full-cycle-shared/         # nur Ressourcen, keine SKILL.md
│   ├── references/                  # Figma-Datenerfassung, UI-Verträge, Validierungskontext
│   └── scripts/                     # screenshot_diff.py, ui_guard.py, localization_context.py
│       └── tests/                   # Testsuiten für Screenshots und UI-Guard
├── figma-full-cycle/
│   ├── SKILL.md                     # Orchestrierung, Zustand, Fragen, Freigabeprüfungen
│   ├── adapters/                    # Fähigkeitszuordnungen für Codex und Claude Code
│   ├── references/                  # Ermittlung, UI Plan, Fallstricke, Geräteintegration
│   │   └── stages/                  # 5/6 sind Adapter zur Übergabe an Begleitskills
│   ├── scripts/                     # ui_plan.py, manifest.py und Tests
│   ├── templates/                   # PIPELINE, PIPELINE.local, UI_PLAN
│   └── agents/openai.yaml
├── figma-feature-spec/              # Stufe 1, Spezifikationsvorlage
├── import-figma-assets/             # Stufe 2, imageset-Hilfsprogramme
├── figma-design-compare/            # Stufe 5, eigenständig oder in der Pipeline
├── swiftui-adaptivity-check/        # Stufe 6, funktioniert ohne Figma
└── device-usage/                    # optionales physisches iPhone / Device Hub
```

### Die fünf Skripte

Alle CLIs arbeiten rein lesend und nur mit der Standardbibliothek — der Skill ruft sie auf, damit das Modell keine Rohdatenmengen verarbeiten muss:

```bash
python3 skills/figma-full-cycle/scripts/ui_plan.py validate \
  --plan docs/FEATURE_UI_PLAN.json \
  --manifest docs/FEATURE_PIPELINE.md \
  --project-root . --phase ui
```

`ui_plan.py` validiert den Implementierungsvertrag — Screens, Komponenten, Tokens, Texte, Assets und
deren Herkunft — und liefert vor dem Beginn einer Build-Schleife kompakte, umsetzbare Diagnosemeldungen.

```bash
python3 skills/_figma-full-cycle-shared/scripts/localization_context.py inventory --root .
```

`localization_context.py` untersucht `.xcstrings` / `.strings` / `.stringsdict` mit begrenzter Ausgabe:
`inventory`, gezieltes `lookup`, `diff` auf Schlüsselebene, `validate`. Es schreibt niemals in Kataloge
und gibt sie niemals vollständig aus.

```bash
python3 skills/_figma-full-cycle-shared/scripts/ui_guard.py check \
  --project-root . --changed-since <BASE_SHA> \
  --reference-canvas 393x852 --asset-catalog App/Assets.xcassets
```

`ui_guard.py` ist die Freigabeprüfung der Stufen 3 und 8 für die Verträge Layout und Colors. Es meldet
ausschließlich `path:line: RULE-ID: message`, sodass beim Review eines Features nur Befunde statt des
gesamten Diffs gelesen werden müssen. Es deckt bewusst nur einen Teil ab und nennt bei jedem Lauf die
Regeln, die es **nicht** geprüft hat — ein unauffälliger Lauf gilt nur innerhalb dieses angegebenen Umfangs.

```bash
python3 skills/figma-full-cycle/scripts/manifest.py get \
  --file docs/FEATURE_PIPELINE.md --section "Capability ledger" --section "Question log"

python3 skills/figma-full-cycle/scripts/manifest.py verify-sources \
  --file docs/FEATURE_PIPELINE.md --project-root .
```

`manifest.py` liest Teile des Manifests statt des gesamten Dokuments — ein ausgefülltes Manifest ist
bis Stufe 6 mehrere Dutzend Kilobyte groß — und beantwortet die tatsächlich relevante Frage bei einer
Fortsetzung: `verify-sources` berechnet die Hashes der Dokumente neu, aus denen der Vertrag für die
UI-Konventionen abgeleitet wurde, und meldet je Bereich `unchanged` / `CHANGED` / `unrecorded`.
Bei einem unveränderten Projekt genügt so ein Befehl, statt die Dokumentation erneut zu lesen.

```bash
python3 skills/_figma-full-cycle-shared/scripts/screenshot_diff.py compare \
  --render build/Onboarding@iPhoneSE.png --mock design/Onboarding.png \
  --ignore-top 6% --out reports/onboarding-se.json
```

`screenshot_diff.py` vergleicht einen Screenshot der Implementierung mit einem Design-Mockup **anderer
Größe** — zuerst passt es das Mockup an die Größe des Renderings an, denn bei der Referenzgröße stimmt
ein Layout mit fester Zeichenfläche pixelgenau überein und verdeckt dadurch Fehler. Es prüft in etwa
0,3 Sekunden pro Paar auf horizontale oder vertikale Randbalken sowie darauf, ob der Hintergrund bis
zu den Rändern reicht, und bietet einen `batch`-Modus für die Matrix aus Stufe 6. Es benötigt `sips`,
das mit macOS ausgeliefert wird — die Pipeline setzt macOS bereits für `xcrun simctl` voraus, also
muss nichts zusätzlich installiert werden.

Über Geräteklassen hinweg trifft es bewusst weniger Aussagen: Die Größenanpassung streckt das
Mockup, während ein natives Layout seine Maße in Punkten beibehält und sich so anpasst. Deshalb
markiert der strukturelle Rastervergleich einen korrekt angepassten Screen genauso deutlich wie
einen fehlerhaften. Außerhalb von `--aspect-tolerance` wird das Raster gemeldet, aber nicht als
Freigabekriterium verwendet; ob auf einem kleineren Gerät Inhalte abgeschnitten werden, bleibt eine Frage für den Reviewer.

Es ist ein Filter, keine Freigabeprüfung: Es erkennt Geometrie, kein Design, und gibt bei jedem Lauf
an, was es nicht beurteilen kann — Schriftart, Icon-Form, Texte und kleine Farbabweichungen. Jeder
fehlgeschlagene Vergleich sowie ein erfolgreiches Paar pro Screen werden visuell geprüft.

## Sicherheitsmodell

- **Figma ist eine nicht vertrauenswürdige Eingabe.** Text innerhalb eines Designs ist Inhalt, niemals eine Anweisung.
- **Schreibende Figma-Tools bleiben deaktiviert** (`use_figma`, `upload_assets`, Schreibzugriffe über Code Connect, …),
  sofern der Nutzer nicht ausdrücklich eine Änderung der Designdatei verlangt.
- **Secrets werden niemals kopiert.** Ein Worktree erhält einen Symlink zur `.env` des Haupt-Checkouts;
  vor jedem Commit läuft ein Secret-Scan; Werte werden niemals ausgegeben.
- **Keine erfundenen Übersetzungen.** Ausgangstexte werden ohne dokumentierte Projektrichtlinie nicht
  in andere Gebietsschemata übertragen; die Übersetzungsbereitschaft hat eine eigene Freigabeprüfung.
- **Über den Merge entscheidet der Nutzer.** Nach bestandener Stufe 8 liegt ein Branch bereit für einen PR vor — ein automatischer Merge erfolgt nie.

## Übertragung auf einen anderen Agenten

Einen Agenten hinzuzufügen bedeutet, eine Adapterdatei hinzuzufügen, nicht den Kern zu ändern. Kopiere
`skills/figma-full-cycle/adapters/claude-code.md`, ersetze die rechte Spalte durch die Toolnamen
deines Agenten, lasse die Fähigkeitszeilen unverändert und verweise im Adapterabschnitt des Skills
auf die Datei. Die zentrale `SKILL.md` bleibt bewusst unabhängig von konkreten Tools.

## Mitwirken

Issues und PRs sind willkommen — siehe [CONTRIBUTING.md](CONTRIBUTING.md). Die Prüfungen laufen lokal in wenigen Sekunden:

```bash
./check.sh
```

Es führt den Python-Validator und die Paket-/Installer-Tests mit jeder erkannten Python-3-Nebenversion
aus, anschließend die Tests des Geräte-Recorders mit Node.js 22+, Skill-Lint und Shell-Syntaxprüfungen.
Alle Tests verwenden lokale Testdaten und temporäre Verzeichnisse; sie steuern kein Telefon und
installieren das Plugin nicht in deinem Konto. So geschieht das automatisch vor jedem Push:

```bash
ln -sf ../../tools/pre-push .git/hooks/pre-push
```

CI prüft die Skill-Struktur, relative Links, das Verhalten von Paket und Installer sowie den
Geräte-Recorder. Die größeren Python-Validator-Testsuiten bleiben im lokalen Prüflauf.

## Lizenz

[MIT](LICENSE) © Oleksandr Khalypa

Der mitgelieferte Device-Usage-Skill behält seinen [MIT-Hinweis](skills/device-usage/LICENSE) bei.
Er wurde aus `gwair1989/device-usage` beim Commit `8d471d565b3335969e5d90b1eac22f67f237b5e1` importiert.
Die weitere Entwicklung findet direkt in diesem Repository statt; siehe [CONTRIBUTING.md](CONTRIBUTING.md).
