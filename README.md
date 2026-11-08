# 项目开发训练题库 · Project Training Skill

**面向完成编程基础学习的人，用真实项目研究设计训练，用实际测试与逐行讲解帮助改进代码。**
**简体中文** | [English](README_EN.md)
`build-project-training` 是一套可由 AI agent 装载的 Skill，配有 Python 命令行工具、评分规范、JSON 模板和历史索引。它把项目训练组织为一套可追溯的流程：调研源码、评估来源、设计题目、验证实现、批改作业，再根据学习记录安排后续训练。

项目旨在帮助学习者从“知道语法”走向“能分析需求、设计模块、验证行为、解释取舍并维护项目”。适用的学习效果仍需通过真实学习过程验证。

## 阅读导航

- [适合谁使用](#适合谁使用)
- [能做什么](#能做什么)
- [运行方式与环境](#运行方式与环境)
- [开始使用](#开始使用)
- [训练题如何生成](#训练题如何生成)
- [作业如何批改](#作业如何批改)
- [目录](#目录)
- [九维标准](#九维标准)
- [命令行入门](#命令行入门)
- [本地检查](#本地检查)
- [交付内容](#交付内容)
- [数据与边界](#数据与边界)
- [常见问题](#常见问题)
- [参与改进](#参与改进)
- [许可证与第三方来源](#许可证与第三方来源)

## 适合谁使用

- 已掌握目标语言基本语法、函数、常用数据结构、文件读写和错误处理，希望通过完整项目继续练习的学习者。
- 希望练习调试、重构、需求变更、测试和性能分析的自学者。
- 需要有验收依据、分层提示和参考实现的教师、助教与学习小组。
- 希望为编程 agent 增加项目训练与作业批改流程的使用者和开发者。

首次使用时，请说明学过的内容、目标语言、运行环境和可投入时间。难度根据这些信息校准；安装依赖的复杂程度不作为进阶能力的替代指标。

## 能做什么

- 默认每套 15 题、3 道基础与 12 道进阶；可指定题数配比、比例或百分比。
- 每次生成前查阅已有资料和网上真实源码，以九维标准评估，满分 100，达到 85 分且满足验证条件才采用。
- 跨语言检查历史重复，从领域、核心概念、成果形式和工程方法增加训练广度。
- 默认交付中文 Word，题目在前，参考代码集中在文末，同时提供源码与评分工具。
- 提交作业后逐行解释作用、给出 0—10 分、说明对错与得分理由、提出修改建议。
- 保留真实测试结果、低分反馈与学习记录，帮助安排下一轮练习。

AI 负责研究、代码审阅和教学判断；Python 工具负责执行清单、保存证据、计算加权分、检查覆盖与维护记录。CLI 本身不会阅读代码后自动生成九维分数。

多语言支持指工作流和验收机制可以适配不同语言；每种实际采用语言均需自己的运行证据。同题多语言版本分别验证，跨组件协作项目还需验证整体接口。

## 运行方式与环境

| 部分 | 负责的工作 |
| --- | --- |
| 装载 Skill 的 agent | 联网调研、理解需求、审阅源码、设计题目、填写九维与逐行评语、组织反馈 |
| Python 工具 | 运行验收、保存执行档案、核算分数、检查逐行覆盖、验证记录并维护索引 |
| 目标语言工具链 | 实际构建、类型检查、行为测试和集成验证 |
| agent 的文档与保存能力 | 制作和检查 Word、整理源码包、保存到用户指定位置 |

模型服务、网络访问、文档处理和文件保存能力由使用者选择的 agent 环境提供。环境要求如下：

- 配套工具使用 **Python 3.10+ 与标准库**。
- 题库和学习历史的写入使用 Linux/WSL 的文件锁；Windows 用户可在 WSL 中执行这些维护命令。
- 目标项目需要自己的运行时、编译器及测试依赖；工具不会自动安装它们。
- 现有跨语言回归样本需要 Node.js 和 g++；只运行 Python 示例时不需要这两项。
- 完整出题流程需要联网查阅源码和实际执行能力；仅有聊天能力的环境应明确报告未完成的验证环节。

## 开始使用

将 [skills/build-project-training](skills/build-project-training) 作为完整 Skill 文件夹，按所用 agent 的技能安装方式装载；入口是 [SKILL.md](skills/build-project-training/SKILL.md)。保留 scripts、references、assets 与 agents 的相对位置。各平台的安装入口可能不同，本仓库不依赖某一种客户端。

如果平台支持显式读取技能文件，也可以让具备文件读取与执行能力的 agent 读取 `SKILL.md`，再按规范完成任务。跨会话的装载与记录保存仍取决于所在平台。

加载后可以直接说：

```text
请使用 build-project-training 制作一套 Python 项目开发训练。
我已学过基础语法、函数、列表与字典、文件读写和异常处理。
环境是 Windows 11 + WSL，优先免费、低依赖的方案。
共 15 题，5 道基础、10 道进阶。
先查阅已有资料和网上真实项目，按原九维标准评估来源，
增加与历史题目的实质差异，全部参考代码集中在文末。
请同时交付验收标准、源码包、评分工具及验证记录。
```

提交作业时可以说：

```text
这是原题要求、运行环境和我提交的全部自写源码。
请按原九维标准给出总评，并逐行说明：
原文件与行号、这行的作用、0—10 分、得分理由、
对错及原因、修改建议和判断依据。
证据不足的地方标为待验证，最后给出最值得先改的 1—3 项。
请保留原提交，修正版另存。
```

同时提供原题、辅助模块、学生自写测试和必要配置，可以减少因上下文缺失造成的误判。

继续下一套时，可以指定“读取之前的历史和学习反馈，使用 JavaScript，基础与进阶比例 2:3，总数 15 题，增加领域与工程方法的广度”。这里对应 6 道基础、9 道进阶；比例不能整除时，按规则取整并说明实际题数。严格比例与总数冲突时需要澄清。

更多请求示例见 [examples/prompts.md](examples/prompts.md)，命令行操作见 [docs/quickstart.md](docs/quickstart.md)。

## 训练题如何生成

1. **读取历史与约束。** 确认语言、版本、平台、先修知识、题目配比和学习反馈，检查已有题目覆盖。
2. **调研真实项目。** 记录检索过程、候选范围与排除理由，阅读固定版本的源码、测试、配置和许可证。
3. **评估并验证来源。** 实际执行适用测试与独立检查，逐项填写九维证据，核算准入结果。
4. **审查题目组合。** 比较历史题和本套题，确认学习目标、难度画像、多样性与新增价值。
5. **编写并验证参考实现。** 先明确验收合同，再实现、构建、测试和复评；协作项目还需整体验证。
6. **交付并记录。** 检查排版、文档代码和源码快照，保存成品，再记录本批次供后续使用。

默认 15 题的研究规则要求至少 45 个去重候选范围，覆盖至少 8 个领域或用途，目标采用不少于 8 个独立上游项目；每个最终方向比较至少两个独立实现。调研与深审按阶段推进，首次构建合格来源库需要实际研究和执行时间。

多样性同时检查领域、核心概念、成果形式和工程方法。仅更换语言、故事、文件名或数据集，不自动算新题。对用户限定的单一领域，按规范说明约束并在其它维度扩展。

缺少网络、源码、运行环境或证据时，先报告真实进度与缺口，保留待验证状态。详细规则见 [SKILL.md](skills/build-project-training/SKILL.md) 与[调研和多样性规范](skills/build-project-training/references/research-diversity.md)。

## 作业如何批改

作业批改使用独立分支：读取原题与原提交，取得适用执行证据，进行九维总评和逐行审阅。批改一份作业不要求重新执行一整套题的候选项目调研。

| 每行反馈 | 说明 |
| --- | --- |
| 原文定位 | 原文件、物理行号、原代码与行类型 |
| 作用 | 该行在完整函数、模块、数据流或控制流中的职责 |
| 教学分 | 0—10 的整数分，并说明得分理由 |
| 对错与原因 | 结合题目要求、源码上下文及实际测试或静态推理说明 |
| 修改建议 | 优先保留学生思路，给出必要的最小修改；合理代码可明确保留 |
| 依据与把握 | 引用实际证据，区分已确认问题、潜在问题和尚缺信息 |

注释、导入、声明、结构行与多行表达式的各个非空物理行都需要审阅。空白行保留并解释分隔作用，标为 **N/A**；缺少依据的判断标为**待验证**，不猜分。

同一个根因建立共享问题，关联受影响行，不按涉及多少行重复扣总分。行分用于教学诊断，**不直接平均为整份作业总分**。

大作业按文件和约 100—200 行分段阅读，保留跨模块上下文，最后检查覆盖情况。未完成范围必须明确列出。修复建议若经过另存副本及相同验收重跑，分别展示前后结果；未经执行的建议保留未验证说明。

低分、编译失败与功能错误的作业仍可获得反馈。原题缺失时，继续可确定的静态解释，正确性总评保持待评。完整字段和判断规则见[作业批改规范](skills/build-project-training/references/homework-marking.md)。

## 目录

| 路径 | 内容 |
| --- | --- |
| [skills/build-project-training/SKILL.md](skills/build-project-training/SKILL.md) | agent 执行入口和出题原则 |
| [skills/build-project-training/references](skills/build-project-training/references) | 九维标准、多语言适配、多样性、交付和批改规范 |
| [skills/build-project-training/scripts](skills/build-project-training/scripts) | 执行器、评分核算、逐行核验、题库维护与回归测试 |
| [skills/build-project-training/assets](skills/build-project-training/assets) | JSON 模板、历史题目索引、运行器验证样本 |
| [docs/quickstart.md](docs/quickstart.md) | 环境、配比计算、真实验收、作业批改与学习记录 |
| [docs/validation.md](docs/validation.md) | 本仓库的验证结果与适用范围 |
| [.github/workflows/checks.yml](.github/workflows/checks.yml) | GitHub Actions 检查配置 |

## 九维标准

| 维度 | 权重 |
| --- | ---: |
| 正确性 Correctness | 20 |
| 可读性与清晰度 Readability & Clarity | 10 |
| 可维护性与可扩展性 Maintainability & Extensibility | 10 |
| 可测试性 Testability | 10 |
| 性能与效率 Performance & Efficiency | 10 |
| 架构与设计质量 Architecture & Design | 15 |
| 文档与可理解性 Documentation | 5 |
| 工程实践与规范 Engineering Practices | 10 |
| 可靠性与健壮性 Reliability & Robustness | 10 |
| **合计** | **100** |

每维给 0—10 的整数分，按 `Σ(单项分 × 权重 ÷ 10)` 计算总分。证据不足为待评，不能补满分。来源准入还检查实际执行、关键缺陷、复用许可与必要复核，详见 [九维规范](skills/build-project-training/references/quality-rubric.md)。

例如正确性 9 分，对总分贡献为 `9 × 20 ÷ 10 = 18` 分。未知维度用 `null`，不补零、不移除该维度，也不重新归一化。

来源与参考实现的准入条件必须同时满足：

- 总分至少 85；正确性至少 9/10，可测试性与可靠性各至少 8/10。
- 任一维出现 0—2 分的严重缺失，阻止准入；85—88 分保留独立复核或盲重评记录。
- 固定源码版本和范围，阅读相关实现与必要文档，实际执行适用测试及独立检查并通过。
- 没有影响采用范围的未解决关键缺陷，复用许可明确，署名和声明义务可以履行。
- 九维均有可定位证据，执行档案能够核验。

外部来源与改编后的参考实现分别审阅。`eligible` 表示满足准入条件，`pending` 表示证据不足，`rejected` 表示已有不满足条件的依据。

85 分用于筛选采用的来源和参考实现；学生的低分作业仍会批改。逐行分是教学诊断，不平均成作业总分；空白行 N/A，不确定行待验证。同一根因用共享问题关联影响行，避免按行数重复扣总分。

## 命令行入门

以下 Bash 命令在 Linux/WSL 的**仓库根目录**执行。运行前先检查被测代码与验收命令。

### 初始化本次工作目录

```bash
SKILL_DIR="$PWD/skills/build-project-training"
mkdir -p work
python3 --version
python3 -B "$SKILL_DIR/scripts/project_grader.py" --help
```

`work/` 用于本地研究、档案和反馈，已被仓库忽略。每次验收与报告使用新的输出目录，且置于被测项目目录之外。

### 计算配比

```bash
python3 -B "$SKILL_DIR/scripts/curate_bank.py" mix \
  --counts 5 10 --basis '学习者要求5道基础、10道进阶'

python3 -B "$SKILL_DIR/scripts/curate_bank.py" mix \
  --ratio 2:3 --basis '学习者要求基础与进阶为2比3'
```

这些命令仅计算配置，不生成题目或修改题库。百分比和取整规则见[学习设计](skills/build-project-training/references/learning-design.md)。

### 跑通已有的 Python 验证样本

以下使用仓库已有样本验证运行器和路径，不是新训练题或合格网上来源。

```bash
python3 -B "$SKILL_DIR/scripts/project_grader.py" run \
  "$SKILL_DIR/assets/validation-fixtures/manifest-python.json" \
  --project "$SKILL_DIR/assets/validation-fixtures" \
  --out "$PWD/work/demo-evidence-01"

python3 -B "$SKILL_DIR/scripts/project_grader.py" verify \
  "$PWD/work/demo-evidence-01/execution.json"

python3 -B "$SKILL_DIR/scripts/project_grader.py" grade \
  "$PWD/work/demo-evidence-01/execution.json" \
  --purpose learner --out "$PWD/work/demo-feedback-01"
```

样本清单包含 12 个用例。成功运行后可在反馈目录查看 `grade.md` 与 `grade.json`；未附九维审阅时，总分仍为待评。保留整个执行档案目录，才能连同源码快照和日志一起复核。

### 作业逐行批改的工具衔接

以下假设已经审查并运行真实作业，得到 `work/submission-evidence-01/execution.json`，且已填写 `work/scope.json`。scope 从 [homework-scope-template.json](skills/build-project-training/assets/homework-scope-template.json) 复制，记录原题、学生文件和有理由排除的文件。

```bash
python3 -B "$SKILL_DIR/scripts/project_grader.py" prepare-homework \
  work/submission-evidence-01/execution.json \
  --scope work/scope.json --out work/homework-review.json
```

草稿生成后，由 agent 阅读完整上下文并填写九维审阅、逐行讲解和共享问题，再执行：

```bash
python3 -B "$SKILL_DIR/scripts/project_grader.py" check-homework \
  work/submission-evidence-01/execution.json --review work/homework-review.json

python3 -B "$SKILL_DIR/scripts/project_grader.py" review-homework \
  work/submission-evidence-01/execution.json --review work/homework-review.json \
  --out work/homework-feedback-01
```

这两项检查/报告命令返回 0 表示批改记录完整，1 表示仍有待评项，2 表示配置、结构或证据不合法。返回 0 不代表九维总分达到 85，也不证明所有 AI 判断正确。

学习记录初始化、`record-attempt`、实际项目验收清单和源码打包步骤见 [docs/quickstart.md](docs/quickstart.md) 与[评分程序规范](skills/build-project-training/references/scoring-program.md)。

## 本地检查

工具使用 Python 3.10+ 和标准库；题库及学习记录的写入使用 Linux/WSL。完整跨语言回归还需 Node.js 与 g++。

在仓库根目录运行：

```bash
python3 -B -m unittest discover \
  -s skills/build-project-training/scripts \
  -p 'test_*.py' -v
```

工具链缺失可能导致相关检查跳过；查看完整输出后再说明验证范围。当前整理版的本地结果见 [验证记录](docs/validation.md)。上传后的 Actions 状态以 GitHub 实际运行结果为准。

仓库配有三组共 68 项回归检查：39 项准入与计划检查、19 项执行与评分流程检查、10 项逐行批改检查。整理版在 **2026-11-04** 的记录为 68 项通过、0 失败、0 跳过，详细环境和范围见验证记录。

已有实测覆盖 Python、Node.js JavaScript、g++ C++17，以及 Python 调用 JavaScript 的协作样本。其他语言保留适配规范，使用前仍需在相应环境实际验证。

## 交付内容

### 制作训练时

- **训练文档：** 默认中文 Word，题目集中在前，来源评估和复盘说明随后，全部参考代码集中在文末。
- **源码包：** 包含可运行实现、必要配置、测试、执行清单和配套评分工具。
- **研究与验证档案：** 保留来源、固定版本、许可、评分依据、执行记录与适用范围。
- **历史索引：** 成品保存并验证后记录批次，供后续去重与扩展使用。

文档与源码应来自同一验证快照；Word 排版、源码提取与重新运行也属于交付验证。保存位置由使用者指定，并以实际可访问、可核验的位置为准。

### 批改作业时

| 文件 | 内容 |
| --- | --- |
| `grade.md` | 九维总评、实际验收结果、共享问题与下一步行动 |
| `line-review.md` | 按原文件和行号排列的完整逐行讲解 |
| `grade.json` | 机器可读总评、验收结果和覆盖统计 |
| `homework-review.json` | 原文定位、证据引用、逐行评语与共享问题记录 |

需要 Word 批改报告时，由 agent 调用相应文档能力排版和检查；逐行内容应完整保留。

## 数据与边界

仓库保留前两套共 30 道题的主题与去重标签，状态均为 `legacy_unreviewed`，未分发原 Word，也未声称这些题通过九维复评。个人文档定位符已从分发版索引移除。合格来源库与学生尝试记录初始为空；真实作业与完整执行档案由使用者另行保存。

这些历史条目不能当作已审阅全文或合格来源使用。使用者需接入自己的原文、运行档案与学习记录；临时命令执行成功不代表记录已经持久化。

研究、学生源码和批改材料可存入独立工作目录。提交公开仓库时，应保留这些个人材料的访问边界；`work/` 已在根目录 `.gitignore` 中忽略。

运行器提供临时副本、超时、输出限制和路径检查，不提供恶意代码沙箱。运行外部项目或学生提交前，应审阅代码与执行命令。测试通过、证据字段完整和摘要相符，都不能单独证明代码质量或 AI 判断正确。

摘要与日志检查可发现错配、缺失和变化，不是防伪签名，不能证明执行者未伪造整套材料。数值评分是有依据的训练判断，不是第三方认证。工具测试也不能用于声称已经证明普遍提升学习效果。

## 常见问题

**一定要练 Python 吗？** 可以按需求选择目标语言。维护工具使用 Python，不限制训练项目的语言；每种实际采用语言都需独立取得相应证据。

**与参考答案写法不同会被判错吗？** 应依据原题要求和可复核行为判断。合理的不同实现可以成立，不因写法不同而判错。

**程序可以一键给任何项目打出客观总分吗？** 程序负责实际执行、核算和一致性检查；需求理解、质量审阅与教学解释仍由 agent 或审阅者完成，缺少依据就保留待评。

**没有网络或目标编译器怎么办？** 继续可验证的已有资料研究或静态解释，说明缺口。新套题的联网来源研究和运行验证仍需补齐，不能用静态检查或另一种语言的结果代替。

**失败或低分作业可以批改吗？** 可以。失败与低分保留在学习历史中，不进入合格源码库。

**再次提交如何看进步？** 先验证原问题是否解决，再检查新问题。同题、同语言、同验收清单和同评分版本等可比条件满足时，学习记录才计算对应变化；不同题目不直接排名。

## 参与改进

欢迎围绕真实使用反馈提交 Issue 或 Pull Request，例如补充某种语言的实际验收适配、改进边界用例、修正报告解释和完善新手文档。

报告问题时，请提供工具链版本、平台、最小可复现代码、验收清单、预期与实际结果，以及相关命令和已脱敏日志。不要公开密码、访问令牌或未经授权的学生材料。

涉及程序行为的修改，请运行相关回归检查并说明新增验证；说明文档的修改应核对命令、相对链接和实际功能。合成测试记录与运行器样本不作为真实合格来源加入题库。

## 许可证与第三方来源

当前分发包尚未包含 `LICENSE` 文件，也未指定统一开源许可证。发布者应根据希望授予的使用、修改与分发权限明确许可，以仓库实际许可证文件为准。可参考 [GitHub 的许可证说明](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)。

后续采用第三方项目时，需分别记录作者、固定版本、链接、采用范围和许可证，履行署名、声明保留及其它适用义务。来源通过质量评估，不会自动改变其授权条件。详见 [NOTICE.md](NOTICE.md)。
