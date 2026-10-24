# Figma Full Cycle

[English](README.md) | [Russian](README.ru.md) | [Simplified Chinese](README.zh-CN.md) | [Hindi](README.hi.md) | [Spanish](README.es.md) | [French](README.fr.md) | [Arabic](README.ar.md) | [German](README.de.md) | [Korean](README.ko.md)

**Entra un frame padre de Figma. Sale una funcionalidad revisada, compilada y conforme a las convenciones del proyecto.**

`figma-full-cycle` es una [Agent Skill](https://code.claude.com/docs/en/skills) de orquestación para
Claude Code y Codex. Le das el enlace al frame padre de una funcionalidad en Figma y dirige todo
el recorrido desde el diseño hasta el código integrado: especificación, recursos, interfaz,
comparación visual, adaptabilidad, lógica y revisión. Lo hace en ocho etapas con criterios de
aprobación, un commit por etapa y un manifiesto versionado como fuente de verdad.

[![Licencia: MIT](https://img.shields.io/badge/License-MIT-black.svg)](LICENSE)
[![CI](https://github.com/gwair1989/figma-full-cycle/actions/workflows/ci.yml/badge.svg)](https://github.com/gwair1989/figma-full-cycle/actions/workflows/ci.yml)
![Skills: 6](https://img.shields.io/badge/skills-6-blue)
![Dependencias de ejecución: ninguna](https://img.shields.io/badge/runtime%20deps-none-brightgreen)
![Interfaz de destino: SwiftUI](https://img.shields.io/badge/target-SwiftUI-orange)

> **Nota sobre el idioma.** Las skills, sus descripciones, los metadatos de agentes, las referencias,
> las plantillas y la documentación del repositorio están en inglés; los archivos localizados
> `README.*.md` son la excepción. [README.md](README.md) es la fuente de las traducciones del README.
> Los documentos que las skills crean en tu proyecto siguen **tu** idioma. La estructura que leen
> las herramientas —claves del UI Plan, estados, encabezados del manifiesto y asuntos de los commits—
> permanece en inglés para que funcionen el validador y la reanudación.

---

## Un plugin, seis puntos de entrada

Este repositorio es tanto una colección de skills reutilizables como un plugin distribuible de Codex.
Instalar el plugin habilita los seis flujos de trabajo; invocar uno no inicia los demás.

| Skill | Uso independiente |
|---|---|
| `figma-full-cycle` | Implementar una funcionalidad completa de Figma; coordina las skills de especificación, recursos, comparación y adaptabilidad |
| `figma-feature-spec` | Redactar una especificación de funcionalidad sin implementar la aplicación |
| `import-figma-assets` | Importar elementos gráficos a un catálogo de recursos de Xcode |
| `figma-design-compare` | Comparar pantallas existentes con un diseño de Figma fijado como referencia |
| `swiftui-adaptivity-check` | Verificar las configuraciones admitidas, con o sin Figma |
| `device-usage` | Probar un iPhone físico mediante Device Hub, sin Figma ni pipeline |

Este es el repositorio canónico de las seis skills. El desarrollo, las incidencias y las versiones
de Device Usage se gestionan aquí; el antiguo repositorio independiente se ha eliminado. Aún puedes
instalar e invocar `device-usage` por separado.

Device Hub es el canal principal del flujo para dispositivos físicos; iPhone Mirroring es la alternativa.
El plugin proporciona instrucciones y un grabador de capturas opcional. No instala Xcode, Computer Use,
un servidor MCP ni permisos de macOS. Las comprobaciones del simulador son independientes; un teléfono
conectado no sustituye a la matriz de adaptabilidad. Las pruebas físicas se incorporan al ciclo completo
solo cuando el usuario o el proyecto las requieren.

## Por qué existe

Una sola instrucción como «implementa esta pantalla de Figma» falla de forma previsible con funcionalidades reales:

| Problema | Qué hace la skill en su lugar |
|---|---|
| El agente inventa un comportamiento de producto que la maqueta estática nunca definió | Cada incógnita se registra como pregunta o como `TBD` explícito; nunca como suposición silenciosa |
| El agente ignora las convenciones del proyecto sobre textos, tipografía y colores | Auditoría de convenciones de solo lectura **antes** de consultar Figma y de editar; cinco líneas de contrato resueltas condicionan cada etapa |
| Los catálogos de localización completos y las respuestas MCP sin procesar consumen la ventana de contexto | Herramientas de solo lectura con salida acotada, consultas de Figma limitadas, delegación a subagentes y evidencias compactas en el estado |
| Un único commit gigantesco que no se puede revisar | Una etapa = un commit, cada uno sujeto a un criterio demostrado con un comando real |
| Se afirma que «todo está en verde» sin ejecutar nada | Los criterios de aprobación exigen evidencia: comando, hora, código de salida y ruta del artefacto |
| El trabajo de diseño deja sucia la rama principal | La funcionalidad se desarrolla en su propia rama y worktree; la limpieza se realiza solo tras confirmar la integración |

## El pipeline

| # | Etapa | Criterio de aprobación (resumido) |
|---|---|---|
| 0 | Worktree: rama, secretos mediante enlaces simbólicos, valores de compilación y compilación/pruebas de referencia | Referencia registrada y manifiesto creado |
| 1 | Especificación + UI Plan: pantallas, mapa de navegación e inventarios de recursos y textos | Especificación y `UI_PLAN.json` en disco, `ui_plan.py --phase ui` correcto y bloqueos resueltos |
| 2 | Recursos: importación según el inventario de node-id | Compilación correcta y presencia de cada recurso verificada |
| 3 | Implementación de la interfaz + estructura de la arquitectura del proyecto | Evidencia del UI Plan actualizada, textos verificados, compilación correcta y todas las pantallas/estados terminados |
| 4 | Refactorización de la interfaz: *condicional*, solo si hay hallazgos | Compilación correcta y comprobaciones afectadas marcadas como `stale` |
| 5 | Comparación de diseño: cada pantalla frente al frame de Figma fijado | Informe en disco, diferencias corregidas y verificadas de nuevo |
| 6 | Adaptabilidad: pantallas pequeñas/grandes, modo claro/oscuro, tamaños de contenido, idiomas y teclado | Sin recortes ni solapamientos; evidencias guardadas |
| 7 | Lógica de negocio + navegación en ejecución + pruebas | `ui_plan.py --phase production` correcto, pruebas superadas y TBD señalados |
| 8 | Revisión final | Revisión sin hallazgos, sin literales sueltos visibles para el usuario y checkpoint limpio guardado en un commit |

Dos propiedades hacen que esto sea viable en la práctica:

- **Reanudar desde cualquier etapa.** El estado está en disco y se concilia con git: `start: stage N`,
  o simplemente pide continuar la funcionalidad.
- **Modo `ui-first`.** ¿Existe el diseño, pero no la especificación? Las etapas 0–6 se ejecutan ahora;
  las preguntas de producto se registran como `deferred-to-spec` en vez de bloquear el trabajo;
  las etapas 7–8 esperan a los requisitos.

## Requisitos

- **Agente:** Claude Code o Codex (un adaptador relaciona cada capacidad con nombres de herramientas concretos).
- **Figma MCP** con acceso de lectura y `FIGMA_ACCESS_TOKEN` para la etapa 5.
- **Python 3.9+**: solo biblioteca estándar; no hay nada que instalar con `pip install`.
- **Proyecto de destino:** una aplicación Xcode/SwiftUI. La arquitectura procede de la documentación
  del proyecto o de una decisión explícita del usuario. Si la documentación falta, es ambigua o
  contradictoria, se pregunta al usuario; el código fuente y las skills instaladas no eligen la
  arquitectura. La decisión y su fuente se registran en el manifiesto y en la especificación antes
  de implementar, también en `ui-first`. Las etapas 3 y 7 siguen esa arquitectura; no se exige
  ningún framework de arquitectura concreto.
- **Las skills complementarias se descubren; no se exigen por nombre.** La comprobación previa
  examina las skills, herramientas MCP, recursos MCP, plugins y scripts locales del proyecto que
  están realmente instalados y asigna uno a cada *rol* de etapa: `design-to-code-workflow`,
  `platform-ui-idiom`, `app-architecture`, `visual-comparison`, `code-review`, etc. Las skills
  renombradas, con namespace, con prefijo de plugin o de proveedores nuevos se detectan igual;
  cada rol sin coincidencias recurre a una alternativa documentada. Solo se fijan por nombre las
  incluidas aquí: `figma-full-cycle`, `figma-feature-spec`, `import-figma-assets`,
  `figma-design-compare`, `swiftui-adaptivity-check` y la opcional `device-usage`. Sus identidades
  se resuelven a los nombres registrados reales, incluidos los namespaces de plugins.
- **Solo para pruebas en un iPhone físico:** macOS, un iPhone físico enlazado, Xcode con Device Hub
  y una herramienta compatible de Computer Use de escritorio para acciones autónomas en la interfaz.
  Sigue las comprobaciones de capacidades de la skill incluida; el diagnóstico por CLI sigue siendo
  posible cuando no hay control gráfico.
- **Grabador opcional de evidencias del dispositivo y sus pruebas:** Node.js 22+, solo biblioteca estándar.

Las capacidades ausentes se presentan al principio en una única lista de bloqueos, en lugar de
ir descubriéndolas una por una a mitad de la compilación. Las asignaciones resultantes, junto con
la comprobación de autenticación de Figma y acceso a los nodos, se escriben en el registro de
capacidades del manifiesto.

## Instalación

### Plugin de Codex

El manifiesto portátil es `plugin.json`; `.codex-plugin/plugin.json` proporciona compatibilidad con
Codex. El marketplace del repositorio es `.agents/plugins/marketplace.json`. Desde esta copia del
repositorio, con una CLI de Codex que incluya `plugin add`:

```bash
git clone https://github.com/gwair1989/figma-full-cycle.git
cd figma-full-cycle
codex plugin marketplace add .
codex plugin add figma-full-cycle@figma-full-cycle-local
```

También puedes seleccionar el marketplace local en el directorio de plugins de la aplicación de
escritorio. Inicia una sesión nueva tras instalar y selecciona la skill por el nombre exacto de
su catálogo; un plugin puede añadir un namespace, por ejemplo `figma-full-cycle:device-usage`.
El paquete sigue el [formato oficial de plugins](https://developers.openai.com/plugins/build/plugins).
Este repositorio es una fuente de distribución local, no una entrada en el directorio público.

### Skills independientes

```bash
git clone https://github.com/gwair1989/figma-full-cycle.git
cd figma-full-cycle
./install.sh
```

`install.sh` crea enlaces simbólicos de las seis skills en `~/.claude/skills`, por lo que `git pull`
las actualiza directamente.

```bash
./install.sh --target ~/.codex/skills   # Codex
./install.sh --target ~/.agents/skills --skill device-usage   # solo el flujo de Device Hub
./install.sh --target ~/.agents/skills --skill figma-feature-spec --skill import-figma-assets
./install.sh --target .claude/skills    # solo este proyecto
./install.sh --copy                     # copiar en vez de crear enlaces simbólicos
./install.sh --force                    # sustituir una skill existente con el mismo nombre
./install.sh --uninstall                # eliminar lo que instaló
```

`--skill` se puede repetir. Seleccionar `figma-full-cycle` instala también sus cuatro complementarias:
`figma-feature-spec`, `import-figma-assets`, `figma-design-compare` y `swiftui-adaptivity-check`.
Device Usage sigue siendo opcional. El ciclo completo y cualquiera de los validadores visuales
instalan `_figma-full-cycle-shared/` una sola vez junto a los directorios de las skills. Contiene
contratos canónicos y utilidades de solo lectura; no tiene `SKILL.md` ni es otro punto de entrada.

```bash
./install.sh --target ~/.codex/skills --copy --skill figma-design-compare
./install.sh --target ~/.codex/skills --copy --skill swiftui-adaptivity-check
```

Las skills visuales copiadas se distribuyen con el directorio hermano `_figma-full-cycle-shared/`;
no necesitan la copia original del repositorio ni la skill del ciclo completo. Usa `--force` para
actualizar una instalación copiada existente. La desinstalación elimina solo los enlaces simbólicos
seleccionados y conserva las skills complementarias y los recursos compartidos para que los demás
consumidores sigan funcionando; los directorios copiados se eliminan manualmente. El árbol de fuentes
también puede utilizarse directamente como plugin, que incluye el directorio compartido.

Para cada skill, utiliza la instalación como plugin o el registro independiente. En Codex, las
invocaciones independientes usan `$<skill-name>`, incluidos `$figma-design-compare` y
`$swiftui-adaptivity-check`. Los mismos directorios funcionan en Claude Code; Device Hub sigue
necesitando Computer Use de escritorio.

¿Ya tienes estas skills en tu directorio de skills? `--force` las sustituye y mueve las copias
anteriores a `.skill-backups`, **junto al** directorio de skills, nunca dentro, donde el agente
podría detectar la copia de seguridad como una segunda skill duplicada.

Verifica la instalación: inicia una sesión nueva del agente y comprueba que `figma-full-cycle`
aparece en la lista de skills.

## Uso

Da a la skill el enlace al frame **padre**, el contenedor que reúne todas las pantallas del flujo,
no a una pantalla aislada:

```text
Ciclo completo desde este frame de Figma: https://figma.com/design/<fileKey>/App?node-id=1234-5678
```

```text
Implementa la funcionalidad de <url>, mode: ui-first — los requisitos vendrán después
```

```text
Continúa <FEATURE>, start: stage 5
```

Puedes hacer las solicitudes en tu idioma; los documentos generados en el proyecto siguen ese idioma.
Usa los enlaces de idiomas de arriba para consultar un README localizado.

### Comprobaciones visuales independientes

```text
Usa $figma-design-compare para comparar estas pantallas implementadas con <Figma URL>; guarda un informe.
Usa $swiftui-adaptivity-check para comprobar estas pantallas en los dispositivos y tamaños de texto admitidos, sin Figma.
```

Las comprobaciones independientes escriben `docs/<RUN>_DESIGN_COMPARE.md` o `docs/<RUN>_ADAPTIVITY.md`,
con artefactos locales en `docs/.cache/<RUN>/`. No necesitan manifiesto del pipeline ni UI Plan,
no crean commits y solo aplican correcciones cuando están autorizadas. Las lecturas MCP autenticadas
bastan para una comparación independiente; el ciclo completo conserva su propia comprobación de
credenciales en la etapa 5. La adaptabilidad no necesita URL, token ni maqueta de Figma; sin maqueta
o `sips`, cada captura nativa se revisa directamente. Las etapas 5/6 invocan estas mismas skills
con el contexto del pipeline e incorporan el informe y las evidencias al manifiesto del orquestador.

### Qué escribe en tu proyecto

| Archivo | Versionado | Función |
|---|---|---|
| `docs/<FEATURE>_PIPELINE.md` | sí | Manifiesto: etapas, criterios de aprobación, evidencias, registro de preguntas y decisiones |
| `docs/<FEATURE>_UI_PLAN.json` | sí | Contrato de traspaso de la especificación a la implementación, comprobado automáticamente |
| `docs/<FEATURE>_PIPELINE.local.md` | no (excluido por gitignore) | Entorno local de ejecución: rutas absolutas y UDID del simulador |

## Contenido del paquete

```
skills/
├── _figma-full-cycle-shared/         # solo recursos, sin SKILL.md
│   ├── references/                  # obtención de datos de Figma, contratos de UI y contexto de validación
│   └── scripts/                     # screenshot_diff.py, ui_guard.py, localization_context.py
│       └── tests/                   # pruebas de capturas y controles de UI
├── figma-full-cycle/
│   ├── SKILL.md                     # orquestación, estado, preguntas y criterios de aprobación
│   ├── adapters/                    # mapas de capacidades para Codex y Claude Code
│   ├── references/                  # descubrimiento, UI Plan, errores frecuentes e integración de dispositivos
│   │   └── stages/                  # 5/6 son adaptadores de delegación a skills complementarias
│   ├── scripts/                     # ui_plan.py, manifest.py y pruebas
│   ├── templates/                   # PIPELINE, PIPELINE.local, UI_PLAN
│   └── agents/openai.yaml
├── figma-feature-spec/              # etapa 1, plantilla de especificación
├── import-figma-assets/             # etapa 2, utilidades de imageset
├── figma-design-compare/            # etapa 5, independiente o dentro del pipeline
├── swiftui-adaptivity-check/        # etapa 6, funciona sin Figma
└── device-usage/                    # iPhone físico / Device Hub, opcional
```

### Los cinco scripts

Todos son CLI de solo lectura basadas únicamente en la biblioteca estándar; la skill los invoca
para que el modelo no tenga que procesar grandes cantidades de datos sin filtrar:

```bash
python3 skills/figma-full-cycle/scripts/ui_plan.py validate \
  --plan docs/FEATURE_UI_PLAN.json \
  --manifest docs/FEATURE_PIPELINE.md \
  --project-root . --phase ui
```

`ui_plan.py` valida el contrato de implementación —pantallas, componentes, tokens, textos, recursos
y su procedencia— y devuelve diagnósticos breves y accionables antes de iniciar el ciclo de compilación.

```bash
python3 skills/_figma-full-cycle-shared/scripts/localization_context.py inventory --root .
```

`localization_context.py` inspecciona `.xcstrings` / `.strings` / `.stringsdict` con salida acotada:
`inventory`, `lookup` dirigido, `diff` por clave y `validate`. Nunca escribe en los catálogos ni los
imprime completos.

```bash
python3 skills/_figma-full-cycle-shared/scripts/ui_guard.py check \
  --project-root . --changed-since <BASE_SHA> \
  --reference-canvas 393x852 --asset-catalog App/Assets.xcassets
```

`ui_guard.py` es el criterio de aprobación de las etapas 3 y 8 para los contratos Layout y Colors.
Solo informa `path:line: RULE-ID: message`, de modo que revisar una funcionalidad consiste en revisar
hallazgos en vez de leer todo el diff. Es deliberadamente parcial e imprime en cada ejecución las
reglas que **no** comprobó; un resultado limpio solo cubre lo indicado en esa nota.

```bash
python3 skills/figma-full-cycle/scripts/manifest.py get \
  --file docs/FEATURE_PIPELINE.md --section "Capability ledger" --section "Question log"

python3 skills/figma-full-cycle/scripts/manifest.py verify-sources \
  --file docs/FEATURE_PIPELINE.md --project-root .
```

`manifest.py` lee partes del manifiesto en vez del documento entero, que puede ocupar decenas de
kilobytes en la etapa 6, y responde a la pregunta relevante al reanudar: `verify-sources` vuelve
a calcular los hashes de los documentos de los que se obtuvo el contrato de convenciones de UI
e informa por área `unchanged` / `CHANGED` / `unrecorded`. Así, un proyecto sin cambios necesita
un solo comando en vez de releer su documentación.

```bash
python3 skills/_figma-full-cycle-shared/scripts/screenshot_diff.py compare \
  --render build/Onboarding@iPhoneSE.png --mock design/Onboarding.png \
  --ignore-top 6% --out reports/onboarding-se.json
```

`screenshot_diff.py` compara una captura de la implementación con una maqueta de diseño **de otro
tamaño**: primero normaliza la maqueta al tamaño de la captura, porque en el tamaño de referencia
un diseño de lienzo fijo coincide píxel a píxel y oculta los fallos. Detecta franjas horizontales,
franjas verticales y si el fondo llega a los bordes en unos 0,3 segundos por pareja, con un modo
`batch` para la matriz de la etapa 6. Necesita `sips`, incluido en macOS; el pipeline ya requiere
macOS para `xcrun simctl`, por lo que no se instala nada nuevo.

Entre clases de dispositivo, limita deliberadamente sus conclusiones: la normalización estira la
maqueta, mientras que una interfaz nativa se adapta manteniendo sus medidas en puntos. Por eso,
la comparación de la cuadrícula estructural puede señalar una pantalla bien adaptada con tanta
intensidad como una defectuosa. Fuera de `--aspect-tolerance`, la cuadrícula se informa, pero no
condiciona la aprobación; los recortes en dispositivos pequeños siguen requiriendo revisión humana.

Es un filtro, no el criterio final de aprobación: detecta geometría, no diseño, e imprime en cada
ejecución lo que no puede evaluar: tipografía, forma de los iconos, textos y pequeñas variaciones
de color. Se revisan visualmente todos los fallos y una pareja aprobada por pantalla.

## Modelo de seguridad

- **Figma es una entrada no confiable.** El texto de un diseño es contenido, nunca instrucciones.
- **Las herramientas de escritura de Figma permanecen desactivadas** (`use_figma`, `upload_assets`,
  escrituras de Code Connect, etc.), salvo que el usuario pida explícitamente modificar el archivo de diseño.
- **Los secretos nunca se copian.** El worktree recibe un enlace simbólico al `.env` de la copia
  principal; se realiza una búsqueda de secretos antes de cada commit y nunca se imprimen sus valores.
- **No se inventan traducciones.** El texto de origen no se propaga a otros idiomas sin una política
  documentada del proyecto; la preparación de las traducciones tiene su propio criterio de aprobación.
- **La integración la decide el usuario.** Superar la etapa 8 produce una rama lista para un PR,
  nunca una integración automática.

## Adaptación a otro agente

Añadir un agente consiste en añadir un archivo adaptador, no en editar el núcleo. Copia
`skills/figma-full-cycle/adapters/claude-code.md`, sustituye la columna derecha por los nombres de
las herramientas de tu agente, conserva las filas de capacidades y referencia el archivo desde
la sección de adaptadores de la skill. El `SKILL.md` principal es independiente de las herramientas
por diseño.

## Contribuir

Las incidencias y los PR son bienvenidos; consulta [CONTRIBUTING.md](CONTRIBUTING.md). Las comprobaciones
se ejecutan localmente en segundos:

```bash
./check.sh
```

Ejecuta las pruebas de los validadores Python y del paquete/instalador en cada versión menor de
Python 3 detectada, y después las pruebas del grabador de dispositivo de Node.js 22+, la validación
de skills y la comprobación de sintaxis de shell. Todas las pruebas usan datos de prueba locales y
directorios temporales; no controlan ningún teléfono ni instalan el plugin en tu cuenta. Para
automatizarlo antes de cada push:

```bash
ln -sf ../../tools/pre-push .git/hooks/pre-push
```

CI comprueba la estructura de las skills, los enlaces relativos, el comportamiento del paquete y
del instalador y el grabador de dispositivo. Las suites más amplias de los validadores Python
permanecen en el ejecutor local.

## Licencia

[MIT](LICENSE) © Oleksandr Khalypa

La skill Device Usage incluida conserva su [aviso MIT](skills/device-usage/LICENSE). Se importó de
`gwair1989/device-usage` en el commit `8d471d565b3335969e5d90b1eac22f67f237b5e1`. El desarrollo
posterior se realiza directamente en este repositorio; consulta [CONTRIBUTING.md](CONTRIBUTING.md).
