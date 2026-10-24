# Figma Full Cycle

[English](README.md) | [Russian](README.ru.md) | [Simplified Chinese](README.zh-CN.md) | [Hindi](README.hi.md) | [Spanish](README.es.md) | [French](README.fr.md) | [Arabic](README.ar.md) | [German](README.de.md) | [Korean](README.ko.md)

**Figma 상위 프레임을 입력하면, 리뷰와 빌드를 마치고 프로젝트 규칙을 준수하는 기능이 완성됩니다.**

`figma-full-cycle`은 Claude Code와 Codex를 위한 오케스트레이터
[Agent Skill](https://code.claude.com/docs/en/skills)입니다. Figma에서 기능의 상위 프레임 링크를
제공하면 디자인부터 코드 병합까지의 전체 과정, 즉 명세, 에셋, UI, 디자인 차이, 적응성, 로직,
리뷰를 진행합니다. 검증 관문이 있는 여덟 단계로 구성되며, 단계마다 한 번씩 커밋하고
버전 관리되는 매니페스트를 기준 정보로 사용합니다.

[![라이선스: MIT](https://img.shields.io/badge/License-MIT-black.svg)](LICENSE)
[![CI](https://github.com/gwair1989/figma-full-cycle/actions/workflows/ci.yml/badge.svg)](https://github.com/gwair1989/figma-full-cycle/actions/workflows/ci.yml)
![스킬: 6](https://img.shields.io/badge/skills-6-blue)
![런타임 의존성: 없음](https://img.shields.io/badge/runtime%20deps-none-brightgreen)
![대상 UI: SwiftUI](https://img.shields.io/badge/target-SwiftUI-orange)

> **언어 안내.** 스킬, 설명, 에이전트 메타데이터, 참고 자료, 템플릿, 저장소 문서는 영어로
> 작성됩니다. 현지화된 `README.*.md` 파일은 예외입니다. [README.md](README.md)가 README
> 번역의 원본입니다. 스킬이 프로젝트에 작성하는 문서는 **사용자의** 언어를 따릅니다.
> 기계가 읽는 구조인 UI Plan 키, 상태, 매니페스트 제목, 커밋 제목은 검증기와 재개 기능이
> 계속 작동하도록 영어로 유지됩니다.

---

## 플러그인 하나, 여섯 가지 진입점

이 저장소는 재사용 가능한 스킬 모음이자 배포 가능한 Codex 플러그인입니다.
플러그인을 설치하면 여섯 워크플로를 모두 사용할 수 있으며, 하나를 호출해도 다른 워크플로가 시작되지는 않습니다.

| 스킬 | 독립적으로 사용할 수 있는 작업 |
|---|---|
| `figma-full-cycle` | Figma 기능 전체 구현. 명세, 에셋, 비교, 적응성 스킬을 조율합니다 |
| `figma-feature-spec` | 앱을 구현하지 않고 기능 명세 작성 |
| `import-figma-assets` | 그래픽 리소스를 Xcode 에셋 카탈로그로 가져오기 |
| `figma-design-compare` | 기존 화면을 고정된 Figma 디자인과 비교 |
| `swiftui-adaptivity-check` | Figma 사용 여부와 관계없이 지원 구성 확인 |
| `device-usage` | Figma나 파이프라인 없이 Device Hub를 통해 실제 iPhone 테스트 |

이곳은 여섯 스킬 모두의 공식 기준 저장소입니다. Device Usage의 개발, 이슈, 릴리스도 이제
이곳에서 관리하며, 기존 독립 저장소는 삭제되었습니다. `device-usage`는 계속 단독으로
설치하고 호출할 수 있습니다.

실제 기기 워크플로의 기본 채널은 Device Hub이며, iPhone Mirroring은 대체 수단입니다.
플러그인은 지침과 선택 사항인 스크린샷 기록기를 제공합니다. Xcode, Computer Use, MCP 서버를
설치하거나 macOS 권한을 설정하지는 않습니다. 시뮬레이터 검사는 별도로 유지됩니다.
연결된 휴대전화 한 대로 적응성 테스트 매트릭스를 대체할 수는 없습니다. 실제 기기 검사는
사용자나 프로젝트가 요구하는 경우에만 전체 사이클에 포함됩니다.

## 이 스킬이 필요한 이유

실제 기능을 구현할 때 “이 Figma 화면을 구현해 줘”라는 프롬프트 하나로는 다음과 같은 문제가 반복됩니다.

| 문제 | 스킬의 대응 방식 |
|---|---|
| 에이전트가 정적 목업에 없는 제품 동작을 임의로 만들어 냄 | 모든 미확정 사항을 질문으로 기록하거나 명시적인 `TBD`로 표시하며, 알리지 않고 추측하지 않습니다 |
| 에이전트가 프로젝트 자체의 문자열 / 타이포그래피 / 색상 규칙을 무시함 | Figma를 읽기 **전**, 그리고 어떤 수정도 하기 전에 규칙을 읽기 전용으로 점검합니다. 확정된 다섯 가지 계약 항목이 모든 단계의 통과 조건이 됩니다 |
| 전체 현지화 카탈로그와 원시 MCP 페이로드가 컨텍스트 윈도우를 소진함 | 범위가 제한된 읽기 전용 도우미, 범위를 지정한 Figma 읽기, 하위 에이전트 위임, 상태에 저장하는 간결한 증거를 사용합니다 |
| 리뷰할 수 없을 만큼 거대한 단일 커밋 | 한 단계 = 한 커밋이며, 각 커밋 전에 실제 명령으로 검증 관문을 통과했음을 증명합니다 |
| 아무것도 실행하지 않고 “모두 통과했다”고 주장함 | 검증 관문에는 명령, 시간, 종료 코드, 산출물 경로라는 증거가 필요합니다 |
| 디자인 구현 작업이 주 브랜치 작업 공간에 미커밋 변경 사항을 남김 | 기능은 전용 브랜치 + worktree에서 작업하며, 병합이 확인된 후에만 정리합니다 |

## 파이프라인

| # | 단계 | 검증 관문(요약) |
|---|---|---|
| 0 | Worktree — 브랜치, 심볼릭 링크로 비밀 정보 연결, 빌드 기본값, 기준 빌드/테스트 | 기준 결과 기록, 매니페스트 생성 |
| 1 | 명세 + UI Plan — 화면, 내비게이션 맵, 에셋 목록, 문구 목록 | 명세와 `UI_PLAN.json`이 디스크에 존재, `ui_plan.py --phase ui` 통과, 진행을 막는 질문에 대한 답변 확보 |
| 2 | 에셋 — node-id 목록을 기준으로 가져오기 | 빌드 성공, 모든 에셋의 존재 확인 |
| 3 | UI 구현 + 프로젝트 아키텍처 골격 | 최신 UI Plan 증거, 문자열 검증 완료, 빌드 성공, 모든 화면/상태 완성 |
| 4 | UI 리팩터링 — 문제가 발견된 경우에만 *조건부* 실행 | 빌드 성공, 영향을 받는 검사를 `stale`로 표시 |
| 5 | 디자인 차이 — 고정된 Figma 프레임과 화면별 비교 | 보고서가 디스크에 존재, 불일치 수정 및 재검사 완료 |
| 6 | 적응성 — 작은/큰 화면, 라이트/다크 모드, 콘텐츠 크기, 로케일, 키보드 | 잘림이나 겹침 없음, 증거 저장 |
| 7 | 비즈니스 로직 + 런타임 내비게이션 + 테스트 | `ui_plan.py --phase production` 통과, 테스트 통과, TBD 표시 |
| 8 | 최종 리뷰 | 미해결 리뷰 지적 사항 없음, 사용자에게 노출되는 미처리 리터럴 없음, 정리된 체크포인트 커밋 완료 |

실제 작업에서 이 과정을 지속할 수 있게 하는 특징은 두 가지입니다.

- **어느 단계에서든 재개.** 상태는 디스크에 저장되고 git과 대조됩니다. `start: stage N`을
  사용하거나, 기능 작업을 계속해 달라고 요청하면 됩니다.
- **`ui-first` 모드.** 디자인은 있지만 명세가 없다면 단계 0–6을 먼저 실행할 수 있습니다.
  제품 관련 질문은 진행을 막는 대신 `deferred-to-spec`으로 기록하며, 단계 7–8은 요구사항을 기다립니다.

## 요구사항

- **에이전트:** Claude Code 또는 Codex. 어댑터가 각 기능을 구체적인 도구 이름에 매핑합니다.
- 읽기 권한이 있는 **Figma MCP**, 그리고 단계 5까지 준비된 `FIGMA_ACCESS_TOKEN`.
- **Python 3.9+** — 표준 라이브러리만 사용하므로 `pip install`로 설치할 항목이 없습니다.
- **대상 프로젝트:** Xcode/SwiftUI 앱. 아키텍처는 프로젝트 문서 또는 사용자의 명시적인 결정에
  따릅니다. 문서가 없거나, 모호하거나, 서로 모순되면 → 사용자에게 질문합니다. 소스 코드와
  설치된 스킬을 근거로 아키텍처를 선택하지 않습니다. `ui-first` 모드에서도 구현 전에 결정과
  그 근거를 매니페스트와 명세에 기록합니다. 단계 3과 7은 해당 아키텍처를 따르며,
  특정 아키텍처 프레임워크를 요구하지 않습니다.
- **보조 스킬은 이름으로 필수 지정하지 않고 탐색합니다.** 사전 점검은 기기에 실제로 설치된
  스킬, MCP 도구, MCP 리소스, 플러그인, 프로젝트 로컬 스크립트를 검색하고, 각 단계의
  *역할*에 하나씩 연결합니다. 역할에는 `design-to-code-workflow`, `platform-ui-idiom`,
  `app-architecture`, `visual-comparison`, `code-review` 등이 있습니다. 이름이 바뀌었거나,
  네임스페이스 또는 플러그인 접두사가 붙었거나, 공급업체가 새로 출시한 스킬도 같은 방식으로
  발견합니다. 일치하는 항목을 찾지 못한 역할은 문서화된 대체 경로를 사용합니다.
  이름이 고정된 것은 이 저장소에 포함된 `figma-full-cycle`, `figma-feature-spec`,
  `import-figma-assets`, `figma-design-compare`, `swiftui-adaptivity-check`와 선택 사항인
  `device-usage`뿐입니다. 포함된 스킬의 식별자는 플러그인 네임스페이스를 포함한 실제 등록
  이름으로 해석됩니다.
- **실제 iPhone 검사에만 필요한 항목:** macOS, 페어링된 실제 iPhone, Device Hub가 포함된 Xcode,
  자율적인 GUI 작업을 지원하는 호환 데스크톱 Computer Use 도구. 포함된 스킬의 기능 점검을
  따르세요. GUI 제어를 사용할 수 없어도 CLI 진단은 가능합니다.
- **선택 사항인 기기 증거 기록기와 해당 테스트:** Node.js 22+, 표준 라이브러리만 사용합니다.

부족한 기능은 빌드 도중 하나씩 발견하는 대신, 시작할 때 하나의 차단 항목 목록으로 보고합니다.
최종 연결 결과와 Figma 인증 및 노드 접근 가능성 검사 결과는 매니페스트의 기능 원장에 기록합니다.

## 설치

### Codex 플러그인

이식 가능한 매니페스트는 `plugin.json`이며, `.codex-plugin/plugin.json`은 Codex 호환성을 지원합니다.
저장소의 마켓플레이스 파일은 `.agents/plugins/marketplace.json`입니다. `plugin add` 명령을 제공하는
Codex CLI를 사용하여 이 저장소의 체크아웃에서 실행하세요.

```bash
git clone https://github.com/gwair1989/figma-full-cycle.git
cd figma-full-cycle
codex plugin marketplace add .
codex plugin add figma-full-cycle@figma-full-cycle-local
```

또는 데스크톱의 Plugins Directory에서 로컬 마켓플레이스를 선택하세요. 설치 후 새 세션을 시작하고
카탈로그에 표시된 정확한 이름으로 스킬을 선택하세요. 플러그인에 따라
`figma-full-cycle:device-usage`처럼 이름에 한정자가 붙을 수 있습니다. 패키징은
[공식 플러그인 형식](https://developers.openai.com/plugins/build/plugins)을 따릅니다.
이 저장소는 로컬 배포 소스이며, 공개 디렉터리에 등록된 항목은 아닙니다.

### 독립형 스킬

```bash
git clone https://github.com/gwair1989/figma-full-cycle.git
cd figma-full-cycle
./install.sh
```

`install.sh`는 여섯 스킬 모두를 `~/.claude/skills`에 심볼릭 링크로 연결하므로,
`git pull`을 실행하면 설치된 스킬도 바로 업데이트됩니다.

```bash
./install.sh --target ~/.codex/skills   # Codex
./install.sh --target ~/.agents/skills --skill device-usage   # Device Hub 워크플로만 설치
./install.sh --target ~/.agents/skills --skill figma-feature-spec --skill import-figma-assets
./install.sh --target .claude/skills    # 이 프로젝트에만 설치
./install.sh --copy                     # 심볼릭 링크 대신 복사
./install.sh --force                    # 같은 이름의 기존 스킬 교체
./install.sh --uninstall                # 이 스크립트가 설치한 항목 제거
```

`--skill`은 반복해서 지정할 수 있습니다. `figma-full-cycle`을 선택하면 네 가지 보조 스킬도 함께 설치합니다.
`figma-feature-spec`, `import-figma-assets`, `figma-design-compare`, `swiftui-adaptivity-check`입니다.
Device Usage는 계속 선택 사항입니다. 전체 사이클 스킬과 두 시각적 검증기 중 어느 것이든 설치하면
스킬 디렉터리 옆에 `_figma-full-cycle-shared/`를 한 번 설치합니다. 이 디렉터리에는 기준 계약과
읽기 전용 도우미가 들어 있습니다. `SKILL.md`가 없으며, 별도의 진입점도 아닙니다.

```bash
./install.sh --target ~/.codex/skills --copy --skill figma-design-compare
./install.sh --target ~/.codex/skills --copy --skill swiftui-adaptivity-check
```

복사 방식으로 설치한 시각적 검사 스킬은 같은 상위 디렉터리의 `_figma-full-cycle-shared/`와
함께 이동해야 합니다. 원본 체크아웃과 전체 사이클 스킬은 필요하지 않습니다. 기존 복사 설치를
업데이트하려면 `--force`를 사용하세요. 제거 명령은 선택한 심볼릭 링크만 제거하며, 다른 사용처가
계속 작동하도록 보조 스킬과 공유 리소스를 보존합니다. 복사된 디렉터리는 직접 제거해야 합니다.
소스 트리는 공유 디렉터리가 포함된 플러그인으로도 직접 사용할 수 있습니다.

스킬마다 플러그인 설치 또는 독립 등록 중 한 가지 방식을 사용하세요. Codex에서 독립형 스킬을
호출할 때는 `$<skill-name>` 형식을 사용합니다. 예를 들면 `$figma-design-compare`와
`$swiftui-adaptivity-check`입니다. 같은 디렉터리를 Claude Code에서도 사용할 수 있습니다.
Device Hub에는 여전히 데스크톱 Computer Use가 필요합니다.

이미 스킬 디렉터리에 이 스킬들을 보관하고 있나요? `--force`는 기존 스킬을 교체하고 이전 복사본을
스킬 디렉터리 **옆에 있는** `.skill-backups`로 옮깁니다. 스킬 디렉터리 안에는 절대 넣지 않습니다.
그 안에 두면 에이전트가 백업을 두 번째 중복 스킬로 인식할 수 있기 때문입니다.

확인 방법: 새 에이전트 세션을 시작하고 스킬 목록에 `figma-full-cycle`이 표시되는지 확인하세요.

## 사용법

스킬에는 단일 화면이 아니라, 흐름의 모든 화면을 담고 있는 컨테이너인 **상위** 프레임의 링크를 제공하세요.

```text
이 Figma 프레임에서 전체 사이클을 진행해 줘: https://figma.com/design/<fileKey>/App?node-id=1234-5678
```

```text
<url>에서 기능을 구현해 줘, mode: ui-first — 요구사항은 나중에 제공할게
```

```text
<FEATURE> 작업을 계속해 줘, start: stage 5
```

자신의 언어로 요청할 수 있으며, 생성되는 프로젝트 문서도 그 언어를 따릅니다.
현지화된 README는 위의 언어 링크에서 확인하세요.

### 독립형 시각적 검사

```text
$figma-design-compare 스킬을 사용해 구현된 이 화면들을 <Figma URL>과 비교하고 보고서를 저장해 줘.
$swiftui-adaptivity-check 스킬을 사용해 Figma 없이 지원 기기와 글자 크기 전반에서 이 화면들을 검사해 줘.
```

독립형 검사는 `docs/<RUN>_DESIGN_COMPARE.md` 또는 `docs/<RUN>_ADAPTIVITY.md`를 작성하고,
로컬 산출물을 `docs/.cache/<RUN>/` 아래에 저장합니다. 파이프라인 매니페스트나 UI Plan은 필요하지
않으며, 커밋하지 않고, 허가된 경우에만 수정 사항을 적용합니다. 독립형 비교에는 인증된 MCP 읽기만으로
충분합니다. 전체 사이클은 자체 단계 5 자격 증명 검사를 유지합니다. 적응성 검사에는 Figma URL,
토큰, 목업이 필요하지 않습니다. 목업이나 `sips`가 없으면 모든 네이티브 캡처를 직접 검토합니다.
단계 5/6은 파이프라인 컨텍스트와 함께 동일한 스킬을 호출하고, 보고서와 증거를 오케스트레이터가
관리하는 매니페스트로 가져옵니다.

### 프로젝트에 작성되는 파일

| 파일 | 버전 관리 | 역할 |
|---|---|---|
| `docs/<FEATURE>_PIPELINE.md` | 예 | 매니페스트: 단계, 검증 관문, 증거, 질문 로그, 결정 사항 |
| `docs/<FEATURE>_UI_PLAN.json` | 예 | 명세에서 구현으로 이어지는, 기계가 검증하는 인계 계약 |
| `docs/<FEATURE>_PIPELINE.local.md` | 아니요(gitignore로 제외) | 로컬 런타임 정보: 절대 경로, 시뮬레이터 UDID |

## 포함된 구성 요소

```
skills/
├── _figma-full-cycle-shared/         # 리소스만 포함, SKILL.md 없음
│   ├── references/                  # Figma 데이터 수집, UI 계약, 검증 컨텍스트
│   └── scripts/                     # screenshot_diff.py, ui_guard.py, localization_context.py
│       └── tests/                   # 스크린샷 및 UI 가드 테스트 모음
├── figma-full-cycle/
│   ├── SKILL.md                     # 조율, 상태, 질문, 검증 관문
│   ├── adapters/                    # Codex 및 Claude Code 기능 매핑
│   ├── references/                  # 탐색, UI Plan, 주의할 점, 기기 통합
│   │   └── stages/                  # 5/6은 보조 스킬 인계 어댑터
│   ├── scripts/                     # ui_plan.py, manifest.py 및 테스트
│   ├── templates/                   # PIPELINE, PIPELINE.local, UI_PLAN
│   └── agents/openai.yaml
├── figma-feature-spec/              # 단계 1, 명세 템플릿
├── import-figma-assets/             # 단계 2, imageset 도우미
├── figma-design-compare/            # 단계 5, 독립형 또는 파이프라인
├── swiftui-adaptivity-check/        # 단계 6, Figma 없이도 작동
└── device-usage/                    # 선택 사항인 실제 iPhone / Device Hub
```

### 다섯 가지 스크립트

모두 읽기 전용이며 표준 라이브러리만 사용하는 CLI입니다. 스킬이 이를 호출하므로 모델이 원시 데이터를
대량으로 직접 처리할 필요가 없습니다.

```bash
python3 skills/figma-full-cycle/scripts/ui_plan.py validate \
  --plan docs/FEATURE_UI_PLAN.json \
  --manifest docs/FEATURE_PIPELINE.md \
  --project-root . --phase ui
```

`ui_plan.py`는 화면, 컴포넌트, 토큰, 문구, 에셋 및 그 출처로 구성된 구현 계약을 검증하고,
빌드 반복 작업을 시작하기 전에 간결하고 실행 가능한 진단 결과를 반환합니다.

```bash
python3 skills/_figma-full-cycle-shared/scripts/localization_context.py inventory --root .
```

`localization_context.py`는 `.xcstrings` / `.strings` / `.stringsdict`를 검사하며 출력 범위를 제한합니다.
제공하는 작업은 `inventory`, 대상을 지정한 `lookup`, 키 단위 `diff`, `validate`입니다.
카탈로그에 절대 쓰지 않으며, 전체 내용을 출력하지도 않습니다.

```bash
python3 skills/_figma-full-cycle-shared/scripts/ui_guard.py check \
  --project-root . --changed-since <BASE_SHA> \
  --reference-canvas 393x852 --asset-catalog App/Assets.xcassets
```

`ui_guard.py`는 Layout 및 Colors 계약에 대한 단계 3과 단계 8의 검증 관문입니다.
`path:line: RULE-ID: message`만 보고하므로, 기능을 리뷰할 때 전체 diff를 읽는 대신 발견된 문제에
집중할 수 있습니다. 의도적으로 일부 규칙만 검사하며, 실행할 때마다 검사하지 **않은** 규칙을
출력합니다. 문제가 없는 실행 결과가 보장하는 범위는 그 안내에 명시된 범위까지입니다.

```bash
python3 skills/figma-full-cycle/scripts/manifest.py get \
  --file docs/FEATURE_PIPELINE.md --section "Capability ledger" --section "Question log"

python3 skills/figma-full-cycle/scripts/manifest.py verify-sources \
  --file docs/FEATURE_PIPELINE.md --project-root .
```

`manifest.py`는 매니페스트 전체가 아닌 일부를 읽습니다. 내용이 채워진 매니페스트는 단계 6쯤 되면
수십 킬로바이트에 달합니다. 이 스크립트는 재개 시 실제로 필요한 질문에 답합니다.
`verify-sources`는 UI 규칙 계약의 근거가 된 문서의 해시를 다시 계산하고, 영역별로
`unchanged` / `CHANGED` / `unrecorded`를 보고합니다. 따라서 변경되지 않은 프로젝트는 문서를
다시 읽는 대신 명령 하나로 확인할 수 있습니다.

```bash
python3 skills/_figma-full-cycle-shared/scripts/screenshot_diff.py compare \
  --render build/Onboarding@iPhoneSE.png --mock design/Onboarding.png \
  --ignore-top 6% --out reports/onboarding-se.json
```

`screenshot_diff.py`는 구현 스크린샷을 **크기가 다른** 디자인 목업과 비교합니다.
먼저 목업을 렌더링 이미지의 크기로 정규화합니다. 기준 크기에서는 고정 캔버스 레이아웃도
픽셀 단위로 일치하여 문제를 숨길 수 있기 때문입니다. 이미지 쌍 하나당 약 0.3초 만에 상하 여백,
좌우 여백, 배경이 가장자리까지 닿는지를 확인하며, 단계 6 매트릭스용 `batch` 모드도 제공합니다.
macOS에 기본 포함된 `sips`가 필요합니다. 파이프라인은 이미 `xcrun simctl` 때문에 macOS를
요구하므로 추가로 설치할 것은 없습니다.

서로 다른 기기 유형을 비교할 때는 의도적으로 판단 범위를 제한합니다. 정규화는 목업을 늘리는
반면, 네이티브 레이아웃은 포인트 단위의 치수를 유지하며 적응합니다. 따라서 구조 그리드 diff는
올바르게 적응한 화면에도 깨진 화면만큼 강하게 문제를 표시할 수 있습니다. `--aspect-tolerance`를
벗어나면 그리드는 보고만 하고 통과 여부 판단에 사용하지 않으며, 작은 기기에서의 잘림 여부는
리뷰어가 판단해야 합니다.

이 도구는 검증 관문 자체가 아니라 선별 도구입니다. 디자인이 아닌 기하학적 형태를 확인하며,
서체, 아이콘 모양, 문구, 미세한 색상 차이처럼 감지하지 못하는 항목을 실행할 때마다 출력합니다.
실패한 모든 이미지 쌍과 각 화면에서 통과한 이미지 쌍 하나는 반드시 눈으로 확인합니다.

## 안전 모델

- **Figma는 신뢰할 수 없는 입력입니다.** 디자인 안의 텍스트는 콘텐츠이며, 절대로 지시가 아닙니다.
- **Figma 쓰기 도구는 비활성 상태를 유지합니다.** `use_figma`, `upload_assets`, Code Connect 쓰기
  등이 해당하며, 사용자가 디자인 파일 수정을 명시적으로 요청한 경우에만 예외입니다.
- **비밀 정보는 절대 복사하지 않습니다.** Worktree는 주 체크아웃의 `.env`를 가리키는 심볼릭 링크를
  사용합니다. 매 커밋 전에 비밀 정보 검사를 실행하며, 값은 절대로 출력하지 않습니다.
- **번역을 임의로 만들어 내지 않습니다.** 문서화된 프로젝트 정책 없이 원문 문구를 다른 로케일에
  일괄 적용하지 않습니다. 번역 준비 상태는 별도의 검증 관문입니다.
- **병합은 사용자가 결정합니다.** 단계 8을 통과하면 PR을 만들 준비가 된 브랜치를 제공하며, 절대로 자동 병합하지 않습니다.

## 다른 에이전트로 이식하기

에이전트 추가는 코어 수정이 아니라 어댑터 파일 하나를 추가하는 작업입니다.
`skills/figma-full-cycle/adapters/claude-code.md`를 복사하고, 오른쪽 열을 해당 에이전트의 도구
이름으로 바꾸세요. 기능 행은 그대로 유지하고, 스킬의 어댑터 섹션에서 이 파일을 참조하세요.
코어 `SKILL.md`는 설계상 특정 도구에 종속되지 않습니다.

## 기여

이슈와 PR을 환영합니다. [CONTRIBUTING.md](CONTRIBUTING.md)를 참고하세요.
검사는 로컬에서 수초 내에 실행됩니다.

```bash
./check.sh
```

이 명령은 감지된 모든 Python 3 마이너 버전에서 Python 검증기와 패키지/설치 프로그램 테스트를
실행한 뒤, Node.js 22+ 기기 기록기 테스트, 스킬 린트, 셸 구문 검사를 실행합니다.
모든 테스트는 로컬 픽스처와 임시 디렉터리를 사용합니다. 휴대전화를 조작하거나 사용자 계정에
플러그인을 설치하지 않습니다. 매번 푸시하기 전에 자동으로 실행하려면 다음 명령을 사용하세요.

```bash
ln -sf ../../tools/pre-push .git/hooks/pre-push
```

CI는 스킬 구조, 상대 링크, 패키지/설치 프로그램 동작, 기기 기록기를 검사합니다.
더 큰 Python 검증기 테스트 모음은 로컬 검사 실행기에서만 실행합니다.

## 라이선스

[MIT](LICENSE) © Oleksandr Khalypa

포함된 Device Usage 스킬은 [MIT 고지](skills/device-usage/LICENSE)를 보존합니다.
`gwair1989/device-usage`의 커밋 `8d471d565b3335969e5d90b1eac22f67f237b5e1`에서 가져왔습니다.
이후 개발은 이 저장소에서 직접 진행합니다. [CONTRIBUTING.md](CONTRIBUTING.md)를 참고하세요.
