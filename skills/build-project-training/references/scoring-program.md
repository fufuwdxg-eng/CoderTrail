# 项目评分程序

## 能力与边界

`project_grader.py` 在 Python 3.10+ 上运行；正式维护题库与学习历史使用 Linux/WSL。先检查项目和命令，再在适合该项目的隔离执行环境运行。运行器有临时工作副本、参数列表、超时、输出限制和路径检查，**不是恶意代码沙箱**，不能承诺隔离网络、内存、系统调用或所有子进程行为。它不会自动安装语言环境。

自动部分采集源码快照、实际命令、运行时版本输出、退出码、耗时、标准输出/错误和用例结果。质量部分沿用原九维权重，由审阅者根据源码和证据填写。未评维度为 null，不补零、不重新归一化、不把测试通过率换算成九维分。耗时包括进程启动，不直接作为跨语言性能排名。

证据摘要检查能识别文件错配、缺失、日志变化和计数不一致，**不是签名或防作弊认证**。执行者可伪造整套材料，提交代码也可能尝试识别测试；要审阅验收合同、断言和独立用例，必要时在隔离环境重跑。字段完整不能替代代码审阅。

## 一次运行

评分工具使用 Python 3.10 及以上版本；学习历史和题库写入在 Linux/WSL 运行。目标项目仍使用自己的真实工具链。将当前技能实际目录记作 SKILL_DIR。把已审查的项目文件放到本次工作目录，复制并填写 `assets/execution-manifest-template.json`。输出目录必须全新且在项目目录之外。

```bash
python3 "$SKILL_DIR/scripts/project_grader.py" run manifest.json --project ./project --out ./evidence-run-01
python3 "$SKILL_DIR/scripts/project_grader.py" verify ./evidence-run-01/execution.json
python3 "$SKILL_DIR/scripts/project_grader.py" grade ./evidence-run-01/execution.json --purpose learner --out ./feedback-01
```

run/verify：0 表示该验收集通过；1 表示失败或未完成；2 表示配置或证据处理出错。缺少工具、未运行、零用例、跳过用例都不算完整通过。失败也保留执行档案与学习诊断。grade 的 learner 模式不以 85 分淘汰作业；admission 模式证据不足或不合格返回非零。

### 执行清单字段

- schema_version=1；project_id 为本次项目标识；languages 为规范语言 ID。
- implementation_mode：single、variants（同合同的多个语言版本）、collaboration（多语言组件协作）。single 恰好一种语言。
- files：明确列出全部采用的源码、测试、配置和必要数据，相对项目目录；不允许目录穿越、符号链接或隐式通配。审阅范围之外的大仓库文件不自动加入。源码摘要为“相对路径到文件 SHA256 的规范 JSON”的 SHA256，包含选定测试和配置。
- steps 按顺序执行；每项含 id、role、languages、argv 数组和可选 timeout_seconds（默认 10，最高 60）。工具链准备应在运行前完成。命令工作目录统一为项目根；用工具自身的配置参数选择子目录。
- role 为 version、build、test 或 integration；每种语言都须有实际版本捕获和行为测试。collaboration 还须至少一个覆盖全部语言的 integration 步骤。
- argv 不经 shell。`{python}` 替换为当前 Python 解释器；其它可执行文件需要已安装。不要把重定向、管道或 shell 字符串直接放进 argv。
- 测试 format=cases：cases 每项含 id、category、stdin、精确预期 stdout，可选 stderr、exit_code（默认 0）；类别为 normal、boundary、error、property、recovery、integration。逐用例独立运行进程；交互状态/数据库/GUI 等项目应使用测试框架与 JUnit 输出。
- 测试 format=junit：提供 result_file 相对路径和 category。运行前删除旧结果，读取新 XML 中实际 testcase 节点；不信任 tests=999 等汇总声明。测试失败、跳过、空文件、无法解析或没有用例均不放行。测试框架需正确传播退出码，审阅者仍须检查断言质量。

命令式示例见 `assets/validation-fixtures/manifest-python.json`、`manifest-javascript.json`、`manifest-cpp.json`、`manifest-collaboration.json`；这些是运行器验证样本，**不是已评分的网上项目，也不是已交付练习**。新语言可用其构建命令与行为用例或 JUnit 结果接入，必须实测后才声称可运行。TypeScript 需额外类型检查与运行时测试。

## 从运行结果到九维评估

先保存整份 evidence 目录，取得持久档案引用；只有 execution.json 而没有 manifest、snapshot 和 logs 无法复核。

```bash
python3 "$SKILL_DIR/scripts/project_grader.py" prepare-review ./evidence-run-01/execution.json --archive-ref '实际保存的档案引用' --kind external_source --out review-draft.json
```

外部来源使用 `--kind external_source`；自己改编的参考实现使用 `--kind reference_implementation`（默认）。两类记录分别评估。

程序只填入已采集事实；id、源码来源、固定版本、许可、code_inspected、independent_checks、九维评分和适用的临界分复核仍须实际审阅后填写。每维给出扣分理由、局限和定位证据。不要自动给九个 9 分。

```bash
python3 "$SKILL_DIR/scripts/project_grader.py" grade ./evidence-run-01/execution.json --review review.json --purpose admission --bank "$SKILL_DIR/assets/question-bank.json" --out ./admission-report
python3 "$SKILL_DIR/scripts/curate_bank.py" add-review review.json
```

grade 输出 grade.json 与中文 grade.md，不自动入库。展示“运行结果”和“九维审阅总分”及其核验状态；只有全部准入条件满足才显示 eligible。参考实现还须提供 `--bank`，核验其合格父来源与必要的各语言独立评估；父来源撤销或档案无法核验时不放行，已确认的拒绝原因不会被缺证据状态覆盖。无审阅文件时仍可产生失败诊断，九维保持待评。审阅文件必须绑定同一源码摘要和同一执行报告；不能将旧评分套在改过的代码上。

`verification.execution_refs` 每项含 local_path、执行报告文件的 sha256 和 archive_ref。跨会话从持久档案取回整个目录；可设置 `TRAINING_EVIDENCE_ROOT`，把证据解包为 `<根目录>/<sha256>/execution.json` 及其伴随文件，程序优先使用该缓存，避免修改历史评估记录。缺证据时 pending；不得凭过去的 eligible 字样放行。

同题多语言版本：先为每种语言创建 single 的独立评估并入库；整体评估的 source.implementation_mode=variants，variant_review_ids 为语言到独立评估 ID 的映射。整体还需覆盖全部版本的运行证据；不能平均低分版本。collaboration 则评整体设计，并强制核验集成测试。

## 学习记录和源码包

复制 learning-observation-template.json，填写 attempt_id、question_id、实际耗时、提示使用、卡点和下次行动；未知用 null。学习反馈不是源码入库许可。

```bash
python3 "$SKILL_DIR/scripts/project_grader.py" record-attempt ./feedback-01/grade.json --observation observation.json --history "$SKILL_DIR/assets/learning-history.json"
python3 "$SKILL_DIR/scripts/project_grader.py" package ./evidence-run-01/execution.json --out ./project-sources.zip
```

历史保留失败和未完成记录，不覆盖旧提交。只有题目、语言、验收清单摘要及评分版本一致时计算前后差值；不同题不排名。自报耗时和提示不冒充自动测量。更新技能内历史后按技能保存流程持久化；完整证据另存档。

源码包来自同一已验证快照，包含 `training-manifest.json` 及 `_training_tools` 评分工具，不携带个人题库和学习历史。解包后从该目录执行下列命令；证据输出放在目录外。Word 也从该快照生成，仍将全部参考代码置于文末。提取文档文件重建、重新运行，再记录交付。

```bash
python3 _training_tools/scripts/project_grader.py run training-manifest.json --project . --out ../replay-evidence
python3 _training_tools/scripts/project_grader.py grade ../replay-evidence/execution.json --purpose learner --out ../replay-feedback
```

## 方法依据

只用于工具实现和核实参数，不作为题库合格代码来源：Python subprocess 文档 https://docs.python.org/3/library/subprocess.html；pytest 输出与 JUnit 文档 https://docs.pytest.org/en/stable/how-to/output.html；Node.js 测试文档 https://nodejs.org/api/test.html。按实际工具版本使用。

## 学生提交作业后的逐行批改

按 [作业批改规范](homework-marking.md) 使用 prepare-homework → agent 填写逐行讲解及九维审阅 → check-homework → review-homework。脚本不自动生成语义判断，负责原文与证据绑定、每行覆盖核验和报告输出。总评仍按原九维权重，行分不平均成总分；空白行 N/A，未知待验证。输出 grade.json 可直接记录学习尝试，低分不淘汰，不自动进入合格源码库。
