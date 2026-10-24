# Figma Full Cycle

[English](README.md) | [Russian](README.ru.md) | [Simplified Chinese](README.zh-CN.md) | [Hindi](README.hi.md) | [Spanish](README.es.md) | [French](README.fr.md) | [Arabic](README.ar.md) | [German](README.de.md) | [Korean](README.ko.md)

**输入一个 Figma 父级画框，交付经过审查、成功构建且符合项目约定的功能。**

`figma-full-cycle` 是面向 Claude Code 和 Codex 的编排型
[Agent Skill](https://code.claude.com/docs/en/skills)。只需提供 Figma 中某项功能的父级画框链接，
它就会推进从设计到代码合并的完整流程——规格说明、资源、UI、设计差异、适配性、逻辑和审查——
分为设有验证关卡的八个阶段，每个阶段对应一次提交，并以纳入版本控制的清单作为事实依据。

[![许可证：MIT](https://img.shields.io/badge/License-MIT-black.svg)](LICENSE)
[![CI](https://github.com/gwair1989/figma-full-cycle/actions/workflows/ci.yml/badge.svg)](https://github.com/gwair1989/figma-full-cycle/actions/workflows/ci.yml)
![技能：6](https://img.shields.io/badge/skills-6-blue)
![运行时依赖：无](https://img.shields.io/badge/runtime%20deps-none-brightgreen)
![目标 UI：SwiftUI](https://img.shields.io/badge/target-SwiftUI-orange)

> **语言说明。** 技能、描述、代理元数据、参考资料、模板和仓库文档均使用英语编写；
> 本地化的 `README.*.md` 文件除外。[README.md](README.md) 是 README 翻译的源文件。
> 技能写入项目的文档会使用**你的**语言。供机器读取的结构——UI Plan 键、状态、清单标题、
> 提交标题——保持英语，以确保验证器和恢复流程正常运行。

---

## 一个插件，六个入口

本仓库既是一组可复用技能，也是可分发的 Codex 插件。
安装插件后即可使用全部六个工作流程；调用其中一个不会启动其他流程。

| 技能 | 可独立用于 |
|---|---|
| `figma-full-cycle` | 实现完整的 Figma 功能；编排规格说明、资源、对比和适配性技能 |
| `figma-feature-spec` | 编写功能规格说明，无需实现应用 |
| `import-figma-assets` | 将图形资源导入 Xcode 资源目录 |
| `figma-design-compare` | 将现有屏幕与锁定的 Figma 设计进行对比 |
| `swiftui-adaptivity-check` | 检查受支持的配置，可使用 Figma，也可不使用 |
| `device-usage` | 通过 Device Hub 测试实体 iPhone，无需 Figma 或流水线 |

本仓库是全部六个技能的权威仓库。Device Usage 的开发、问题跟踪和版本发布现已迁入此处；
原独立仓库已移除。你仍可单独安装和调用 `device-usage`。

Device Hub 是实体设备工作流程的主要通道，iPhone Mirroring 则作为备用方案。
插件提供操作说明和可选的截图记录器。它不会安装 Xcode、Computer Use、MCP 服务器，
也不会授予 macOS 权限。模拟器检查仍单独进行；连接一部手机不能替代适配性测试矩阵。
只有用户或项目要求时，实体设备检查才会加入完整流程。

## 为什么需要它

对于真实功能，一句“实现这个 Figma 屏幕”的提示往往会出现以下问题：

| 问题 | 技能如何应对 |
|---|---|
| 代理凭空编造静态设计稿从未包含的产品行为 | 每个未知项都会成为已记录的问题或明确的 `TBD`，绝不默默猜测 |
| 代理忽略项目自身的字符串、字体排版或颜色约定 | 在读取 Figma 和任何编辑**之前**进行只读约定审计；五条已明确的契约约束每个阶段 |
| 完整本地化目录和原始 MCP 载荷耗尽上下文窗口 | 使用限制读取范围的只读辅助工具、限定范围的 Figma 读取、子代理委派，以及状态中的精简证据 |
| 一次庞大且无法审查的提交 | 一个阶段对应一次提交，每次提交前都要通过实际命令证明满足关卡要求 |
| 没有运行任何检查就声称“全部通过” | 关卡要求提供证据：命令、时间、退出码和产物路径 |
| 实现设计后在主干工作区留下未提交的改动 | 功能在专用分支和 worktree 中运行；仅在确认合并后清理 |

## 流水线

| # | 阶段 | 验证关卡（简述） |
|---|---|---|
| 0 | Worktree——分支、通过符号链接提供密钥、构建默认值、基线构建与测试 | 记录基线，创建清单 |
| 1 | 规格说明 + UI Plan——屏幕、导航图、资源清单、文案清单 | 规格说明和 `UI_PLAN.json` 已写入磁盘，`ui_plan.py --phase ui` 通过，阻塞问题已得到回答 |
| 2 | 资源——按 node-id 清单导入 | 构建成功，确认每项资源均已存在 |
| 3 | UI 实现 + 项目架构骨架 | UI Plan 证据为最新，字符串已验证，构建成功，每个屏幕和状态均已完成 |
| 4 | UI 重构——*有条件执行*，仅在发现问题时进行 | 构建成功，受影响的检查标记为 `stale` |
| 5 | 设计差异——逐屏对比锁定的 Figma 画框 | 报告已写入磁盘，差异已修复并重新检查 |
| 6 | 适配性——小屏与大屏、浅色与深色模式、内容尺寸、语言区域、键盘 | 无裁切或重叠，证据已保存 |
| 7 | 业务逻辑 + 运行时导航 + 测试 | `ui_plan.py --phase production` 通过，测试通过，TBD 项已标明 |
| 8 | 最终审查 | 审查无未解决问题，无遗漏的面向用户的字面量，已提交干净的检查点 |

两个特性让这套流程能够在实际项目中顺利运行：

- **从任意阶段恢复。** 状态保存在磁盘上，并与 git 核对——使用 `start: stage N`，
  或直接要求继续该功能。
- **`ui-first` 模式。** 已有设计，但还没有规格说明？阶段 0–6 可立即执行；产品问题记录为
  `deferred-to-spec`，不会阻塞流程；阶段 7–8 则等待需求明确后再进行。

## 环境要求

- **代理：** Claude Code 或 Codex（适配器将每项能力映射到具体工具名称）。
- 具有读取权限的 **Figma MCP**，并在阶段 5 前提供 `FIGMA_ACCESS_TOKEN`。
- **Python 3.9+**——仅使用标准库，无需 `pip install` 任何包。
- **目标项目：** Xcode/SwiftUI 应用。架构依据项目文档或用户的明确决定。
  文档缺失、含糊或相互矛盾时 → 询问用户；源代码和已安装技能不能代替架构选择。
  实现前会将决定及其来源记录到清单和规格说明中，`ui-first` 模式也不例外。
  阶段 3 和 7 遵循该架构；不要求使用某个特定的架构框架。
- **配套技能通过发现机制确定，不要求特定名称。** 预检会扫描你机器上实际安装的技能、
  MCP 工具、MCP 资源、插件和项目本地脚本，并为每个阶段的*角色*绑定其中一项——
  `design-to-code-workflow`、`platform-ui-idiom`、`app-architecture`、`visual-comparison`、
  `code-review` 等。改名后、带命名空间、带插件前缀或供应商新推出的技能，都会以相同方式被识别；
  找不到匹配项的角色都会采用有文档说明的后备方案。只有本仓库随附的技能按名称固定：
  `figma-full-cycle`、`figma-feature-spec`、`import-figma-assets`、`figma-design-compare`、
  `swiftui-adaptivity-check`，以及可选的 `device-usage`。随附技能的标识会解析为其实际注册名称，
  包括插件命名空间。
- **仅针对实体 iPhone 检查：** macOS、已配对的实体 iPhone、带 Device Hub 的 Xcode，
  以及可自主执行 GUI 操作的兼容桌面 Computer Use 工具。请遵循随附技能的能力检查；
  GUI 控制不可用时，仍可通过 CLI 进行诊断。
- **可选的设备证据记录器及其测试：** Node.js 22+，仅使用标准库。

缺失的能力会在开始时汇总为一份阻塞项列表，不会等构建进行到一半才逐个发现。
最终绑定结果以及 Figma 身份验证和节点可达性探测结果，都会写入清单的能力台账。

## 安装

### Codex 插件

可移植的清单文件是 `plugin.json`；`.codex-plugin/plugin.json` 用于兼容 Codex。
仓库的插件市场文件是 `.agents/plugins/marketplace.json`。使用提供 `plugin add` 命令的
Codex CLI，在此仓库的检出目录中执行：

```bash
git clone https://github.com/gwair1989/figma-full-cycle.git
cd figma-full-cycle
codex plugin marketplace add .
codex plugin add figma-full-cycle@figma-full-cycle-local
```

也可以在桌面端的 Plugins Directory 中选择本地插件市场。安装后请开启新会话，
并按技能目录中显示的准确名称选择技能；插件可能会为名称添加限定前缀，
例如 `figma-full-cycle:device-usage`。打包方式遵循
[官方插件格式](https://developers.openai.com/plugins/build/plugins)。
本仓库是本地分发源，并非公共目录中的条目。

### 独立技能

```bash
git clone https://github.com/gwair1989/figma-full-cycle.git
cd figma-full-cycle
./install.sh
```

`install.sh` 将全部六个技能以符号链接形式安装到 `~/.claude/skills`，因此 `git pull` 会直接更新它们。

```bash
./install.sh --target ~/.codex/skills   # Codex
./install.sh --target ~/.agents/skills --skill device-usage   # 仅安装 Device Hub 工作流程
./install.sh --target ~/.agents/skills --skill figma-feature-spec --skill import-figma-assets
./install.sh --target .claude/skills    # 仅用于此项目
./install.sh --copy                     # 复制而非创建符号链接
./install.sh --force                    # 替换已有的同名技能
./install.sh --uninstall                # 移除本脚本安装的内容
```

`--skill` 可重复使用。选择 `figma-full-cycle` 时，还会安装它的四个配套技能：
`figma-feature-spec`、`import-figma-assets`、`figma-design-compare`、`swiftui-adaptivity-check`。
Device Usage 始终为可选项。完整流程技能以及两个视觉验证技能中的任意一个，都会在技能目录旁
安装一份 `_figma-full-cycle-shared/`。该目录包含权威契约和只读辅助工具，
没有 `SKILL.md`，也不是额外的技能入口。

```bash
./install.sh --target ~/.codex/skills --copy --skill figma-design-compare
./install.sh --target ~/.codex/skills --copy --skill swiftui-adaptivity-check
```

复制安装的视觉技能需与同级的 `_figma-full-cycle-shared/` 目录一起迁移；不需要原始仓库检出目录
或完整流程技能。使用 `--force` 更新已有的复制安装。卸载仅移除选定的符号链接，
并保留配套技能和共享资源，以便其他使用方继续正常工作；复制的目录需要手动移除。
源代码树也可以直接作为插件使用，其中包含共享目录。

对于每个技能，请选择插件安装或独立注册其中一种方式。Codex 中独立注册技能的调用形式为
`$<skill-name>`，例如 `$figma-design-compare` 和 `$swiftui-adaptivity-check`。
同样的目录也可用于 Claude Code；Device Hub 仍需要桌面 Computer Use。

你的技能目录中已经有这些技能？`--force` 会替换它们，并将旧副本移到技能目录**旁边**的
`.skill-backups` 中，绝不会放进技能目录内部，否则代理会把备份识别为第二个重复技能。

验证方法：开启新的代理会话，确认技能列表中出现 `figma-full-cycle`。

## 使用

向技能提供**父级**画框的链接——即包含整个流程所有屏幕的容器，而非单个屏幕：

```text
从这个 Figma 画框开始完整流程：https://figma.com/design/<fileKey>/App?node-id=1234-5678
```

```text
根据 <url> 实现功能，mode: ui-first——需求稍后提供
```

```text
继续 <FEATURE>，start: stage 5
```

你可以使用自己的语言提出请求；生成的项目文档也会使用该语言。
本地化的 README 可通过上方的语言链接查看。

### 独立视觉检查

```text
使用 $figma-design-compare 将这些已实现的屏幕与 <Figma URL> 对比，并保存报告。
使用 $swiftui-adaptivity-check 在受支持的设备和文字大小下检查这些屏幕，无需 Figma。
```

独立检查会写入 `docs/<RUN>_DESIGN_COMPARE.md` 或 `docs/<RUN>_ADAPTIVITY.md`，
本地产物位于 `docs/.cache/<RUN>/`。它们不需要流水线清单或 UI Plan，不会提交代码，
且只有获得授权后才会应用修复。独立对比只需经过身份验证的 MCP 读取权限；
完整流程仍保留自身的阶段 5 凭据检查。适配性检查不需要 Figma URL、令牌或设计稿；
没有设计稿或 `sips` 时，会直接审查每一张原生截图。阶段 5/6 在流水线上下文中调用同样的技能，
并将报告和证据导入由编排器管理的清单。

### 写入项目的内容

| 文件 | 纳入版本控制 | 用途 |
|---|---|---|
| `docs/<FEATURE>_PIPELINE.md` | 是 | 清单：阶段、关卡、证据、问题日志、决定 |
| `docs/<FEATURE>_UI_PLAN.json` | 是 | 从规格说明到实现、由机器检查的交接契约 |
| `docs/<FEATURE>_PIPELINE.local.md` | 否（由 gitignore 忽略） | 本地运行信息：绝对路径、模拟器 UDID |

## 包含哪些内容

```
skills/
├── _figma-full-cycle-shared/         # 仅含资源，无 SKILL.md
│   ├── references/                  # Figma 获取方式、UI 契约、验证上下文
│   └── scripts/                     # screenshot_diff.py、ui_guard.py、localization_context.py
│       └── tests/                   # 截图和 UI 守卫测试套件
├── figma-full-cycle/
│   ├── SKILL.md                     # 编排、状态、问题、关卡
│   ├── adapters/                    # Codex 和 Claude Code 能力映射
│   ├── references/                  # 能力发现、UI Plan、常见陷阱、设备集成
│   │   └── stages/                  # 5/6 是配套技能的交接适配器
│   ├── scripts/                     # ui_plan.py、manifest.py 及测试
│   ├── templates/                   # PIPELINE、PIPELINE.local、UI_PLAN
│   └── agents/openai.yaml
├── figma-feature-spec/              # 阶段 1，规格说明模板
├── import-figma-assets/             # 阶段 2，imageset 辅助工具
├── figma-design-compare/            # 阶段 5，可独立使用或用于流水线
├── swiftui-adaptivity-check/        # 阶段 6，无需 Figma 也可使用
└── device-usage/                    # 可选的实体 iPhone / Device Hub
```

### 五个脚本

全部是只读、仅依赖标准库的 CLI——技能调用这些工具，让模型无需处理海量原始数据：

```bash
python3 skills/figma-full-cycle/scripts/ui_plan.py validate \
  --plan docs/FEATURE_UI_PLAN.json \
  --manifest docs/FEATURE_PIPELINE.md \
  --project-root . --phase ui
```

`ui_plan.py` 验证实现契约——屏幕、组件、设计令牌、文案、资源及其来源——
并在开始构建循环前返回精简、可执行的诊断结果。

```bash
python3 skills/_figma-full-cycle-shared/scripts/localization_context.py inventory --root .
```

`localization_context.py` 检查 `.xcstrings` / `.strings` / `.stringsdict`，并限制输出范围：
`inventory`、定向 `lookup`、键级别的 `diff`、`validate`。它绝不会写入本地化目录，
也绝不会完整输出目录内容。

```bash
python3 skills/_figma-full-cycle-shared/scripts/ui_guard.py check \
  --project-root . --changed-since <BASE_SHA> \
  --reference-canvas 393x852 --asset-catalog App/Assets.xcassets
```

`ui_guard.py` 是阶段 3 和阶段 8 针对 Layout 和 Colors 契约的验证关卡。它只报告
`path:line: RULE-ID: message`，不输出其他内容，因此审查功能时只需关注发现的问题，
不必通读差异。它有意只覆盖部分规则，每次运行都会列出**没有**检查的规则——
一次无问题的运行所能证明的范围，仅限于该说明中明确的范围。

```bash
python3 skills/figma-full-cycle/scripts/manifest.py get \
  --file docs/FEATURE_PIPELINE.md --section "Capability ledger" --section "Question log"

python3 skills/figma-full-cycle/scripts/manifest.py verify-sources \
  --file docs/FEATURE_PIPELINE.md --project-root .
```

`manifest.py` 按部分读取清单，而不是读取全部内容——到阶段 6，一份填写完整的清单可能达到
数十 KB——并回答恢复流程真正需要解决的问题：`verify-sources` 重新计算用于确定 UI 约定契约的
文档哈希值，按领域报告 `unchanged` / `CHANGED` / `unrecorded`，因此对于未发生变化的项目，
只需一条命令，无需重新阅读文档。

```bash
python3 skills/_figma-full-cycle-shared/scripts/screenshot_diff.py compare \
  --render build/Onboarding@iPhoneSE.png --mock design/Onboarding.png \
  --ignore-top 6% --out reports/onboarding-se.json
```

`screenshot_diff.py` 将实现截图与**不同尺寸**的设计稿进行对比——先将设计稿归一化到渲染图的尺寸，
因为在参考尺寸下，固定画布布局会逐像素匹配，从而掩盖布局问题。它每对图片约需 0.3 秒，
即可判断是否存在上下留边、左右留边，以及背景是否延伸到边缘，并提供 `batch` 模式用于阶段 6 的
测试矩阵。它需要 macOS 自带的 `sips`——流水线原本就因 `xcrun simctl` 而要求 macOS，
因此无需安装额外工具。

跨设备类别时，它会有意限制结论范围：归一化会拉伸设计稿，而原生布局会保持以点为单位的尺寸
并进行适配，因此结构网格差异会对正确适配的屏幕和损坏的屏幕发出同样明显的提示。
超出 `--aspect-tolerance` 时，网格结果仅供报告，不作为关卡判定依据；
较小设备上是否发生裁切，仍需要审查者判断。

它是筛选工具，而非关卡：它能识别几何关系，不能理解设计，并在每次运行时列出其无法识别的内容——
字体、图标形状、文案、细微色差。每一对未通过的图片，以及每个屏幕的一对通过图片，
都必须经过目视审查。

## 安全模型

- **Figma 是不可信输入。** 设计中的文字是内容，绝不是指令。
- **Figma 写入工具保持禁用**（`use_figma`、`upload_assets`、Code Connect 写入等），
  除非用户明确要求修改设计文件。
- **绝不复制密钥。** Worktree 通过符号链接访问主检出目录中的 `.env`；
  每次提交前都会扫描密钥；绝不输出密钥值。
- **不凭空生成翻译。** 没有成文的项目政策时，不会将源文案批量写入其他语言区域；
  翻译就绪检查是独立的关卡。
- **是否合并由用户决定。** 通过阶段 8 后会得到可提交 PR 的分支，绝不会自动合并。

## 适配其他代理

添加代理只需新增一个适配器文件，无需编辑核心。复制
`skills/figma-full-cycle/adapters/claude-code.md`，将右列替换为你的代理的工具名称，
保留所有能力行，并在技能的适配器章节中引用该文件。核心 `SKILL.md` 按设计保持与具体工具无关。

## 贡献

欢迎提交问题和 PR——参见 [CONTRIBUTING.md](CONTRIBUTING.md)。检查在本地运行，几秒内即可完成：

```bash
./check.sh
```

它会在每个检测到的 Python 3 次版本上运行 Python 验证器及打包/安装器测试，
然后运行 Node.js 22+ 设备记录器测试、技能 lint 和 shell 语法检查。
所有测试均使用本地固定测试数据和临时目录；不会操作手机，也不会将插件安装到你的账户。
要在每次推送前自动执行这些检查：

```bash
ln -sf ../../tools/pre-push .git/hooks/pre-push
```

CI 检查技能结构、相对链接、打包/安装器行为和设备记录器。
较大的 Python 验证器测试套件仍由本地检查运行器执行。

## 许可证

[MIT](LICENSE) © Oleksandr Khalypa

随附的 Device Usage 技能保留其 [MIT 声明](skills/device-usage/LICENSE)。它从
`gwair1989/device-usage` 导入，对应提交为 `8d471d565b3335969e5d90b1eac22f67f237b5e1`。
后续开发直接在本仓库进行；参见 [CONTRIBUTING.md](CONTRIBUTING.md)。
