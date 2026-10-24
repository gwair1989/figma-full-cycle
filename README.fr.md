# Figma Full Cycle

[English](README.md) | [Russian](README.ru.md) | [Simplified Chinese](README.zh-CN.md) | [Hindi](README.hi.md) | [Spanish](README.es.md) | [French](README.fr.md) | [Arabic](README.ar.md) | [German](README.de.md) | [Korean](README.ko.md)

**Un cadre parent Figma en entrée. Une fonctionnalité revue, compilée et conforme aux conventions en sortie.**

`figma-full-cycle` est une [compétence d’agent](https://code.claude.com/docs/en/skills) d’orchestration pour
Claude Code et Codex. Fournissez-lui le lien vers le cadre parent d’une fonctionnalité dans Figma ; elle pilote
tout le parcours, de la conception au code fusionné — spécification, ressources graphiques, interface, comparaison visuelle, adaptabilité, logique, revue —
en huit étapes soumises à validation, avec un commit par étape et un manifeste versionné comme source de référence.

[![Licence : MIT](https://img.shields.io/badge/License-MIT-black.svg)](LICENSE)
[![Intégration continue](https://github.com/gwair1989/figma-full-cycle/actions/workflows/ci.yml/badge.svg)](https://github.com/gwair1989/figma-full-cycle/actions/workflows/ci.yml)
![Compétences : 6](https://img.shields.io/badge/skills-6-blue)
![Dépendances d’exécution : aucune](https://img.shields.io/badge/runtime%20deps-none-brightgreen)
![Interface cible : SwiftUI](https://img.shields.io/badge/target-SwiftUI-orange)

> **Note sur la langue.** Les compétences, descriptions, métadonnées des agents, références, modèles et documents
> du dépôt sont rédigés en anglais ; les fichiers `README.*.md` traduits font exception. [README.md](README.md)
> est la source des traductions du README. Les documents que les compétences écrivent dans votre projet sont rédigés dans
> **votre** langue. La structure lue par les outils — clés de UI Plan, statuts, titres du manifeste, titres
> des commits — reste en anglais pour que le validateur et la reprise continuent de fonctionner.

---

## Un plugin, six points d’entrée

Ce dépôt est à la fois une collection de compétences réutilisables et un plugin Codex distribuable.
Installer le plugin rend les six parcours disponibles ; en invoquer un ne lance pas les autres.

| Compétence | Utilisation indépendante |
|---|---|
| `figma-full-cycle` | Implémenter une fonctionnalité Figma complète ; orchestre les compétences de spécification, de ressources graphiques, de comparaison et d’adaptabilité |
| `figma-feature-spec` | Rédiger la spécification d’une fonctionnalité sans implémenter l’application |
| `import-figma-assets` | Importer des éléments graphiques dans un catalogue de ressources Xcode |
| `figma-design-compare` | Comparer des écrans existants à une conception Figma fixée comme référence |
| `swiftui-adaptivity-check` | Vérifier les configurations prises en charge, avec ou sans Figma |
| `device-usage` | Tester un iPhone physique via Device Hub, sans Figma ni pipeline |

Il s’agit du dépôt de référence pour les six compétences. Le développement, les tickets et les versions de Device Usage
se trouvent désormais ici ; l’ancien dépôt indépendant a été supprimé. Vous pouvez toujours installer et invoquer
`device-usage` seule.

Device Hub est le canal principal du parcours sur appareil physique ; iPhone Mirroring est sa solution de repli.
Le plugin fournit des instructions et un enregistreur facultatif de captures d’écran. Il n’installe ni Xcode,
ni Computer Use, ni serveur MCP, et n’accorde pas les autorisations macOS. Les vérifications sur simulateur restent distinctes ; un téléphone
connecté ne remplace pas la matrice d’adaptabilité. Les vérifications sur appareil physique ne rejoignent le cycle complet que si
l’utilisateur ou le projet l’exige.

## Pourquoi cette compétence existe

Une simple consigne « implémente cet écran Figma » échoue de manière prévisible sur de vraies fonctionnalités :

| Échec | Ce que fait la compétence à la place |
|---|---|
| L’agent invente un comportement produit absent d’une maquette statique | Chaque inconnue devient une question consignée ou un `TBD` explicite — jamais une supposition silencieuse |
| L’agent ignore les conventions du projet en matière de chaînes de texte, de typographie ou de couleurs | Audit des conventions en lecture seule **avant** Figma et avant toute modification ; cinq clauses du contrat doivent être résolues pour valider chaque étape |
| Les catalogues de localisation entiers et les données MCP brutes saturent la fenêtre de contexte | Outils auxiliaires bornés en lecture seule, lectures Figma ciblées, délégation à des sous-agents, preuves compactes dans l’état |
| Un commit géant impossible à relire | Une étape = un commit, chacun soumis à une validation démontrée par une commande réelle |
| « Tout est au vert » annoncé sans rien exécuter | Les validations exigent des preuves : commande, heure, code de sortie, chemin de l’artefact |
| Le travail de conception laisse la branche principale avec des modifications non enregistrées | La fonctionnalité dispose de sa propre branche et de son propre arbre de travail ; nettoyage uniquement après confirmation de la fusion |

## Le pipeline

| # | Étape | Critère de passage (abrégé) |
|---|---|---|
| 0 | Arbre de travail — branche, secrets par liens symboliques, paramètres de compilation par défaut, compilation/tests de référence | État de référence enregistré, manifeste créé |
| 1 | Spécification + UI Plan — écrans, carte de navigation, inventaire des ressources graphiques, inventaire des textes | Spécification et `UI_PLAN.json` sur disque, réussite de `ui_plan.py --phase ui`, réponses aux questions bloquantes |
| 2 | Ressources graphiques — importation selon l’inventaire des identifiants de nœuds | Compilation réussie, présence de chaque ressource vérifiée |
| 3 | Implémentation de l’interface + structure initiale de l’architecture du projet | Preuves associées à UI Plan à jour, chaînes vérifiées, compilation réussie, chaque écran et chaque état terminés |
| 4 | Refactorisation de l’interface — *conditionnelle*, uniquement en cas de constats | Compilation réussie, vérifications concernées marquées `stale` |
| 5 | Comparaison visuelle — comparaison de chaque écran au cadre Figma fixé comme référence | Rapport sur disque, écarts corrigés et vérifiés de nouveau |
| 6 | Adaptabilité — petits/grands écrans, modes clair/sombre, tailles de contenu, paramètres régionaux, clavier | Aucun contenu tronqué ni chevauchement, preuves conservées |
| 7 | Logique métier + navigation à l’exécution + tests | Réussite de `ui_plan.py --phase production`, tests réussis, points TBD signalés |
| 8 | Revue finale | Revue sans problème, aucune chaîne littérale indésirable exposée à l’utilisateur, point de contrôle propre enregistré dans un commit |

Deux propriétés rendent ce parcours viable en pratique :

- **Reprendre à n’importe quelle étape.** L’état réside sur disque et est réconcilié avec git — `start: stage N`,
  ou demandez simplement de poursuivre la fonctionnalité.
- **Mode `ui-first`.** La conception existe, mais pas la spécification ? Les étapes 0–6 s’exécutent maintenant ; les questions produit sont
  enregistrées sous `deferred-to-spec` au lieu de bloquer ; les étapes 7–8 attendent les exigences.

## Prérequis

- **Agent :** Claude Code ou Codex (un adaptateur associe chaque capacité à des noms d’outils concrets).
- **Figma MCP** avec accès en lecture, et `FIGMA_ACCESS_TOKEN` au plus tard à l’étape 5.
- **Python 3.9+** — bibliothèque standard uniquement, rien à installer via `pip install`.
- **Projet cible :** une application Xcode/SwiftUI. L’architecture est déterminée par la documentation du projet
  ou par une décision explicite de l’utilisateur. Documentation absente, ambiguë ou contradictoire → interroger l’utilisateur ;
  le code source et les compétences installées ne choisissent pas l’architecture. La décision et sa source sont
  consignées dans le manifeste et la spécification avant l’implémentation, y compris en mode `ui-first`. Les étapes 3 et 7
  suivent cette architecture ; aucun framework d’architecture particulier n’est requis.
- **Les compétences complémentaires** sont **découvertes, et non imposées par leur nom.** La vérification préalable parcourt les compétences,
  outils MCP, ressources MCP, plugins et scripts locaux au projet effectivement installés sur votre machine, et
  en associe un à chaque *rôle* d’étape — `design-to-code-workflow`, `platform-ui-idiom`,
  `app-architecture`, `visual-comparison`, `code-review`, … Les compétences de fournisseurs renommées, dotées d’un espace de noms,
  préfixées par un plugin ou entièrement nouvelles sont reconnues de la même manière ; chaque rôle sans correspondance utilise un
  parcours de repli documenté. Seuls les éléments fournis ici sont fixés par leur nom : `figma-full-cycle`, `figma-feature-spec`,
  `import-figma-assets`, `figma-design-compare`, `swiftui-adaptivity-check`, et la compétence facultative `device-usage`. Les identités fournies sont résolues vers leurs véritables
  noms enregistrés, espaces de noms des plugins compris.
- **Pour les vérifications sur iPhone physique uniquement :** macOS, un iPhone physique jumelé, Xcode avec Device Hub et un
  outil Computer Use de bureau compatible pour les actions autonomes dans l’interface graphique. Suivez les vérifications de capacités
  de la compétence fournie ; les diagnostics en ligne de commande restent possibles lorsque le contrôle de l’interface graphique est indisponible.
- **Pour l’enregistreur facultatif de preuves sur appareil et ses tests :** Node.js 22+, bibliothèque standard uniquement.

Les capacités manquantes sont signalées dès le départ dans une seule liste de blocages, plutôt que découvertes une par une
à mi-chemin de la compilation. Les associations obtenues — ainsi que la vérification de l’authentification Figma et de l’accessibilité
des nœuds — sont inscrites dans le registre des capacités du manifeste.

## Installation

### Plugin Codex

Le manifeste portable est `plugin.json` ; `.codex-plugin/plugin.json` assure la compatibilité avec Codex.
La place de marché du dépôt est `.agents/plugins/marketplace.json`. Depuis cette copie du dépôt, avec une interface en ligne de commande Codex
qui propose `plugin add` :

```bash
git clone https://github.com/gwair1989/figma-full-cycle.git
cd figma-full-cycle
codex plugin marketplace add .
codex plugin add figma-full-cycle@figma-full-cycle-local
```

Vous pouvez aussi sélectionner la place de marché locale dans le répertoire des plugins de l’application de bureau. Ouvrez une nouvelle
session après l’installation et sélectionnez la compétence sous le nom exact affiché dans son catalogue ; un plugin
peut le qualifier, par exemple `figma-full-cycle:device-usage`. Le paquet suit le
[format officiel des plugins](https://developers.openai.com/plugins/build/plugins).
Ce dépôt est une source de distribution locale, pas une entrée du répertoire public.

### Compétences indépendantes

```bash
git clone https://github.com/gwair1989/figma-full-cycle.git
cd figma-full-cycle
./install.sh
```

`install.sh` crée des liens symboliques vers les six compétences dans `~/.claude/skills` — ainsi, `git pull` les met à jour sur place.

```bash
./install.sh --target ~/.codex/skills   # Codex
./install.sh --target ~/.agents/skills --skill device-usage   # parcours Device Hub uniquement
./install.sh --target ~/.agents/skills --skill figma-feature-spec --skill import-figma-assets
./install.sh --target .claude/skills    # ce projet uniquement
./install.sh --copy                     # copier au lieu de créer des liens symboliques
./install.sh --force                    # remplacer une compétence existante du même nom
./install.sh --uninstall                # supprimer ce que le script a installé
```

`--skill` peut être répété. Sélectionner `figma-full-cycle` installe également ses quatre compétences complémentaires :
`figma-feature-spec`, `import-figma-assets`, `figma-design-compare`, `swiftui-adaptivity-check`.
Device Usage reste facultative. Le cycle complet et chacun des deux validateurs visuels installent
`_figma-full-cycle-shared/` une seule fois, à côté des répertoires des compétences. Ce répertoire contient les contrats de référence
et les outils auxiliaires en lecture seule, n’a pas de `SKILL.md` et ne constitue pas un autre point d’entrée.

```bash
./install.sh --target ~/.codex/skills --copy --skill figma-design-compare
./install.sh --target ~/.codex/skills --copy --skill swiftui-adaptivity-check
```

Les compétences visuelles copiées sont accompagnées du répertoire voisin `_figma-full-cycle-shared/` ; la copie d’origine
du dépôt et la compétence du cycle complet ne sont pas nécessaires. Utilisez `--force` pour mettre à jour une installation copiée
existante. La désinstallation ne supprime que les liens symboliques sélectionnés et conserve les compétences complémentaires ainsi que les ressources partagées
pour que les autres composants qui les utilisent continuent de fonctionner ; les répertoires copiés doivent être supprimés manuellement. L’arborescence source est
également utilisable directement comme plugin, lequel inclut le répertoire partagé.

Pour chaque compétence, choisissez soit l’installation du plugin, soit l’enregistrement indépendant. Dans Codex, les appels indépendants
utilisent `$<skill-name>`, notamment `$figma-design-compare` et `$swiftui-adaptivity-check`.
Les mêmes répertoires fonctionnent dans Claude Code ; Device Hub nécessite toujours Computer Use sur le bureau.

Ces compétences sont déjà présentes dans votre répertoire de compétences ? `--force` les remplace et déplace les anciennes
copies vers `.skill-backups` **à côté** du répertoire des compétences — jamais à l’intérieur, où un agent
détecterait la sauvegarde comme une deuxième compétence en doublon.

Vérification : ouvrez une nouvelle session d’agent et assurez-vous que `figma-full-cycle` apparaît dans la liste des compétences.

## Utilisation

Donnez à la compétence le lien vers le cadre **parent** — le conteneur qui regroupe tous les écrans du parcours,
et non un écran isolé :

```text
Cycle complet à partir de ce cadre Figma : https://figma.com/design/<fileKey>/App?node-id=1234-5678
```

```text
Implémente la fonctionnalité à partir de <url>, mode: ui-first — les exigences viendront plus tard
```

```text
Poursuis <FEATURE>, start: stage 5
```

Vous pouvez formuler vos demandes dans votre langue ; les documents générés pour le projet suivent cette langue.
Utilisez les liens de langues ci-dessus pour consulter un README traduit.

### Vérifications visuelles indépendantes

```text
Utilise $figma-design-compare pour comparer ces écrans implémentés à <Figma URL> ; enregistre un rapport.
Utilise $swiftui-adaptivity-check pour vérifier ces écrans sur les appareils et tailles de texte pris en charge, sans Figma.
```

Les vérifications indépendantes écrivent `docs/<RUN>_DESIGN_COMPARE.md` ou `docs/<RUN>_ADAPTIVITY.md`, avec des artefacts
locaux sous `docs/.cache/<RUN>/`. Elles ne nécessitent ni manifeste de pipeline ni UI Plan, ne créent pas de commits et
n’appliquent des corrections que lorsqu’elles sont autorisées. Les lectures MCP authentifiées suffisent pour une comparaison indépendante ;
le cycle complet conserve sa propre vérification des identifiants à l’étape 5. La vérification d’adaptabilité ne nécessite ni URL Figma, ni jeton, ni maquette ;
sans maquette ou sans `sips`, chaque capture native est examinée directement. Les étapes 5/6 appellent ces mêmes
compétences avec le contexte du pipeline et importent le rapport et les preuves dans le manifeste géré par l’orchestrateur.

### Ce qui est écrit dans votre projet

| Fichier | Versionné | Rôle |
|---|---|---|
| `docs/<FEATURE>_PIPELINE.md` | oui | Manifeste : étapes, critères de passage, preuves, journal des questions, décisions |
| `docs/<FEATURE>_UI_PLAN.json` | oui | Contrat de transmission de la spécification à l’implémentation, vérifié automatiquement |
| `docs/<FEATURE>_PIPELINE.local.md` | non (ignoré par git) | Données d’exécution locales : chemins absolus, UDID du simulateur |

## Contenu de la distribution

```
skills/
├── _figma-full-cycle-shared/         # ressources uniquement, sans SKILL.md
│   ├── references/                  # acquisition Figma, contrats d’interface, contexte de validation
│   └── scripts/                     # screenshot_diff.py, ui_guard.py, localization_context.py
│       └── tests/                   # suites de tests des captures d’écran et du garde-fou d’interface
├── figma-full-cycle/
│   ├── SKILL.md                     # orchestration, état, questions, critères de passage
│   ├── adapters/                    # correspondances des capacités de Codex et Claude Code
│   ├── references/                  # découverte, UI Plan, pièges, intégration de l’appareil
│   │   └── stages/                  # 5/6 sont des adaptateurs de transmission aux compétences complémentaires
│   ├── scripts/                     # ui_plan.py, manifest.py et tests
│   ├── templates/                   # PIPELINE, PIPELINE.local, UI_PLAN
│   └── agents/openai.yaml
├── figma-feature-spec/              # étape 1, modèle de spécification
├── import-figma-assets/             # étape 2, outils auxiliaires imageset
├── figma-design-compare/            # étape 5, indépendante ou dans le pipeline
├── swiftui-adaptivity-check/        # étape 6, fonctionne sans Figma
└── device-usage/                    # iPhone physique / Device Hub, facultatif
```

### Les cinq scripts

Tous sont des outils en ligne de commande en lecture seule, limités à la bibliothèque standard — la compétence les appelle pour que le modèle n’ait jamais à absorber les données brutes :

```bash
python3 skills/figma-full-cycle/scripts/ui_plan.py validate \
  --plan docs/FEATURE_UI_PLAN.json \
  --manifest docs/FEATURE_PIPELINE.md \
  --project-root . --phase ui
```

`ui_plan.py` valide le contrat d’implémentation — écrans, composants, jetons de conception, textes, ressources graphiques et
leur provenance — et renvoie des diagnostics concis et exploitables avant le début d’une boucle de compilation.

```bash
python3 skills/_figma-full-cycle-shared/scripts/localization_context.py inventory --root .
```

`localization_context.py` inspecte les fichiers `.xcstrings` / `.strings` / `.stringsdict` avec des sorties bornées :
`inventory`, `lookup` ciblé, `diff` au niveau des clés, `validate`. Il n’écrit jamais dans les catalogues et ne
les affiche jamais en entier.

```bash
python3 skills/_figma-full-cycle-shared/scripts/ui_guard.py check \
  --project-root . --changed-since <BASE_SHA> \
  --reference-canvas 393x852 --asset-catalog App/Assets.xcassets
```

`ui_guard.py` est le contrôle de passage des étapes 3 et 8 pour les contrats Layout et Colors. Il ne signale que
`path:line: RULE-ID: message`, afin que la revue d’une fonctionnalité porte sur les constats plutôt que sur
la lecture du diff entier. Il est volontairement partiel et affiche à chaque exécution les règles qu’il n’a **pas**
vérifiées — une exécution sans erreur n’atteste donc que du périmètre décrit par cette note.

```bash
python3 skills/figma-full-cycle/scripts/manifest.py get \
  --file docs/FEATURE_PIPELINE.md --section "Capability ledger" --section "Question log"

python3 skills/figma-full-cycle/scripts/manifest.py verify-sources \
  --file docs/FEATURE_PIPELINE.md --project-root .
```

`manifest.py` lit des parties du manifeste plutôt que sa totalité — un manifeste rempli atteint des dizaines de kilooctets
à l’étape 6 — et répond à la vraie question d’une reprise : `verify-sources` recalcule les empreintes des documents
à partir desquels le contrat de conventions d’interface a été établi et indique, pour chaque domaine, `unchanged` / `CHANGED` /
`unrecorded`. Ainsi, un projet inchangé ne nécessite qu’une commande au lieu d’une relecture de sa documentation.

```bash
python3 skills/_figma-full-cycle-shared/scripts/screenshot_diff.py compare \
  --render build/Onboarding@iPhoneSE.png --mock design/Onboarding.png \
  --ignore-top 6% --out reports/onboarding-se.json
```

`screenshot_diff.py` compare une capture d’écran de l’implémentation à une maquette **de taille
différente** — il ajuste d’abord la maquette à la taille du rendu, car à la taille de référence une mise en page sur un canevas fixe
correspond pixel pour pixel et masque les défauts. Il repère les bandes horizontales et verticales et vérifie si
l’arrière-plan atteint les bords en environ 0,3 s par paire, avec un mode `batch` pour la matrice de l’étape 6. Il
nécessite `sips`, fourni avec macOS — le pipeline exige déjà macOS pour `xcrun simctl`, donc
aucune installation supplémentaire n’est nécessaire.

Entre catégories d’appareils, ses conclusions sont volontairement plus limitées : l’ajustement étire la maquette, tandis qu’une mise en page
native s’adapte en conservant ses mesures en points ; la comparaison de grille structurelle signale donc un écran correctement adapté
aussi fortement qu’un écran défectueux. Au-delà de `--aspect-tolerance`, la grille est signalée sans conditionner le passage, et
la présence de contenu tronqué sur un appareil plus petit reste à l’appréciation du réviseur.

C’est un filtre, pas le contrôle de passage : il voit la géométrie, pas la conception, et affiche à chaque exécution ce qu’il
ne peut pas détecter — police de caractères, forme des icônes, textes, légères variations de couleur. Chaque échec et une paire
réussie par écran font l’objet d’un examen visuel.

## Modèle de sécurité

- **Figma est une entrée non fiable.** Le texte d’une conception est du contenu, jamais une instruction.
- **Les outils d’écriture Figma restent désactivés** (`use_figma`, `upload_assets`, écritures Code Connect, …), sauf si
  l’utilisateur demande explicitement de modifier le fichier de conception.
- **Les secrets ne sont jamais copiés.** Un arbre de travail reçoit un lien symbolique vers le `.env` de la copie principale du dépôt ; une analyse
  de détection des secrets est exécutée avant chaque commit ; les valeurs ne sont jamais affichées.
- **Aucune traduction inventée.** Les textes sources ne sont pas propagés vers d’autres paramètres régionaux sans politique de projet
  documentée ; la préparation à la traduction fait l’objet d’une validation distincte.
- **La fusion relève de l’utilisateur.** Réussir l’étape 8 produit une branche prête pour une demande de fusion — jamais une fusion automatique.

## Adaptation à un autre agent

Ajouter un agent consiste à ajouter un fichier d’adaptateur, sans modifier le cœur. Copiez
`skills/figma-full-cycle/adapters/claude-code.md`, remplacez la colonne de droite par les noms des outils de votre
agent, conservez les lignes de capacités intactes et référencez-le dans la section des adaptateurs de la compétence. Le fichier central
`SKILL.md` reste indépendant des outils par conception.

## Contribuer

Les tickets et demandes de fusion sont les bienvenus — voir [CONTRIBUTING.md](CONTRIBUTING.md). Les vérifications s’exécutent localement, en quelques secondes :

```bash
./check.sh
```

Cette commande exécute le validateur Python et les tests du paquet et de l’installateur sur chaque version mineure
de Python 3 détectée, puis les tests de l’enregistreur sur appareil sous Node.js 22+, l’analyse statique des compétences et les vérifications de syntaxe shell.
Tous les tests utilisent des données de test locales et des répertoires temporaires ; ils ne pilotent aucun téléphone et n’installent pas
le plugin dans votre compte. Pour automatiser ces vérifications avant chaque push :

```bash
ln -sf ../../tools/pre-push .git/hooks/pre-push
```

L’intégration continue vérifie la structure des compétences, les liens relatifs, le comportement du paquet et de l’installateur, ainsi que l’enregistreur sur appareil.
Les suites plus volumineuses du validateur Python restent dans le lanceur de vérifications local.

## Licence

[MIT](LICENSE) © Oleksandr Khalypa

La compétence Device Usage fournie conserve sa [mention de licence MIT](skills/device-usage/LICENSE). Elle a été
importée depuis `gwair1989/device-usage` au commit `8d471d565b3335969e5d90b1eac22f67f237b5e1`.
Son développement se poursuit directement dans ce dépôt ; voir [CONTRIBUTING.md](CONTRIBUTING.md).
