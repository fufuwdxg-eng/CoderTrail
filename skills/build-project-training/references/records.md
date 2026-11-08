# 记录格式与命令

目录：路径与用途 · 评估记录 · 批次计划 · 持久化规则

## 路径与用途

先找到当前个人技能的实际目录，记为 SKILL_DIR；安装后目录名称可能变化，不硬编码最初的文件夹名。主脚本以自身位置寻找 `assets/question-bank.json`。

- `assets/question-bank.json`：唯一持续维护的来源评估、已交付题目及批次索引。
- `assets/review-template.json`：评估记录空模板。复制到本次工作目录填写，不直接填模板。
- `assets/plan-template.json`：批次计划空模板。
- `scripts/curate_bank.py`：核算评分、核验执行档案、计算多样性及原子更新；不替代代码审阅。
- `scripts/project_grader.py` 和 `execution_runner.py`：实际执行、证据检查、中文反馈和学习历史，使用 [评分程序](scoring-program.md)。
- `assets/homework-scope-template.json`：作业要求、学生文件与有理由的排除范围；逐行评语草稿由 prepare-homework 生成，不能预填虚构得分。
- `scripts/homework_review.py`：逐行原文/覆盖核验及批改报告，见 [作业批改规范](homework-marking.md)。
- `assets/learning-history.json`：学习尝试与可比变化，失败也保留，与合格源码库分开。
- `scripts/test_curate_bank.py`：脚本维护用边界测试，测试数据是虚构的，绝不进入真实合格库。

运行示例：`python3 "$SKILL_DIR/scripts/curate_bank.py" stats`。读取 JSON 输出中的 `history_signature` 填入计划。`--bank PATH` 必须放在子命令之前；默认使用技能内题库，测试时才使用临时题库。

## 评估记录

所有必填字段见空模板。`kind` 为 `external_source` 或 `reference_implementation`。ID 使用有版本信息的稳定标识，例如项目、组件与 commit 的组合，不能复用 ID 覆盖不同评估。

`source` 字段：

- `url`：实际读取的源码永久链接，或生成实现的持久文件引用。
- `project_url`：外部项目根链接，用于统计独立来源；镜像归并为同一项目。
- `revision`：固定 commit、已解析的 release 或文件版本；不能为 main、master、latest、HEAD。
- `code_sha256`：必须等于评分程序 execution.json 的 code_sha256，即路径到文件摘要映射的规范 JSON 摘要，包含所选源码、测试和配置。原先其它摘要算法的记录须重建对应执行档案。
- `implementation_mode`：single、variants 或 collaboration。variants 另填 variant_review_ids，逐语言关联已入库的独立参考实现；子实现文件必须与整体快照中的同路径文件相同。collaboration 必须有通过的集成测试。
- `scope`：被读取/采用文件、函数、依赖与使用规模。
- `evidence_archive_ref`：保存了复现日志、源码摘要或检查记录的持久引用；不能只有会失效的临时路径。
- `license`：id、实际许可文本 locator、reuse_allowed 布尔值或 null，以及 obligations 字符串。独立实现可注明 original，并记录父来源要求。
- `languages`：被评代码范围内的实际语言 ID 列表，非空且去重；如 `["cpp"]` 或 `["typescript", "go"]`。按语言适配规则统一标识，不根据 `.h` 等含糊扩展名猜语言。

`evidence` 是列表，每项含 id、kind、locator、observation。kind 至少区分 source、test、documentation、benchmark、configuration、license。locator 定位到固定版本代码行或已保存日志；observation 记录实际观察。

九个 `scores` 键与评分规范完全一致，每项含 `rating`（0–10 整数或 null）、`evidence_ids`、`rationale` 与 `limitations`。没有发现实质局限也要说明检查范围，不以“无”掩盖未检查内容。

`verification` 记录实际读取和运行，commands 是执行过的命令列表，environment 写编译器/解释器/运行时、平台和依赖版本，evidence_ids 必须关联 test 类型证据。`independent_checks=true` 只能用于已经补充并运行独立检查的情况。critical_findings=[] 表示审查后未发现未解决关键问题；没有审查不能填 true。

`verification.language_checks` 与 `source.languages` 逐项对应，每项包含 language、environment、commands、evidence_ids、tests_passed。证据须含相应语言的实际行为测试，不只编译或类型检查。旧记录缺失这些字段会变成 pending，不补写虚构结果。多语言协作还需在整体 verification 命令与证据中保存接口和集成检查；分别提供同题多语言版本时用独立评估 ID，必要时另建覆盖全部实现的整体评估供题目关联。

`verification.execution_refs` 必填，包含完整执行档案的 local_path、sha256、archive_ref。检查实际快照/日志/清单、用例结果、语言和集成状态；不可访问或摘要不符不能放行。跨会话使用评分程序文档中的证据缓存路径。85–88 分另填 calibration；任一维严重缺失阻断。

改编实现增加 `parent_review_ids`，引用题库中 eligible 的外部来源；单独评估本次代码，不复用上游评分。先为实现及其测试记录保存持久引用，才能正式加入题库。

命令：

```
python3 "$SKILL_DIR/scripts/curate_bank.py" score review.json
python3 "$SKILL_DIR/scripts/curate_bank.py" add-review review.json
python3 "$SKILL_DIR/scripts/curate_bank.py" revoke-review REVIEW_ID --reason '具体撤销理由'
```

`score` 核算单条评估及其执行证据；参考实现的父来源与多语言版本关系还必须通过 `grade --bank`、`add-review` 和最终计划检查。

总分满足但缺证据仍为 pending；总分不足或关键检查失败为 rejected；只有 eligible 可 add-review。相同 ID、相同内容重复添加是幂等操作；相同 ID 的不同内容报冲突。评估变更时新增版本化 ID。撤销记录保留历史但不再可采用。

## 批次计划

`batch_id`、`count`、`basic_count`、`history_signature` 必填。新计划同时记录 advanced_count 和 difficulty_request；默认总数 15、基础 3、进阶 12。15 题内调整配比是正常配置，无需总数豁免；只有总题数改变时才须用 scope_override_reason 记录用户依据。旧计划若只用 scope_override_reason 记录了自定义配比，仍可读取，不改写历史。

difficulty_request 含 mode、value、basis。mode 为 default（value=null）、counts（value=[基础题数,进阶题数]）、ratio（value=[基础权重,进阶权重]）或 percentage（value=基础百分比）。自定义时 basis 必须记录用户原话或明确沿用依据。比例/百分比按基础题数四舍五入、半题向上，进阶补足总数；明确告知取整结果。严格比例冲突按学习设计规则处理。程序核验原始请求与计划题数一致，再检查每题实际难度标签。

只计算配置、不读写题库的命令：

```bash
python3 "$SKILL_DIR/scripts/curate_bank.py" mix
python3 "$SKILL_DIR/scripts/curate_bank.py" mix --counts 5 10 --basis '用户要求5道基础10道进阶'
python3 "$SKILL_DIR/scripts/curate_bank.py" mix --ratio 2:3 --basis '用户要求基础与进阶为2比3'
python3 "$SKILL_DIR/scripts/curate_bank.py" mix --basic-percent 50 --basis '用户要求基础占一半，采用已说明的取整规则'
```

将返回的 count、basic_count、advanced_count、difficulty_request 填回计划。rounding_applied 提示是否近似分配，不由用户手填决定。`check-plan` 重算并报告实际配置；`record-batch` 保存配置和请求依据。用户仅给一类题数时先计算另一类再用 counts；不能用计算器的成功输出替代用户授权或其它计划检查。

`research` 中保留：

- history_checked、completed_at：确已完成前置研究，completed_at 为带时区时间。
- query_log：含 query、date 的真实检索记录。
- candidates：至少 3N 个真实候选，逐项含 id、url、project_url、scope、languages、domain_tags、disposition。已批准来源的候选 id 与 review id 相同，languages 与被评范围一致；对照但未选项可为独立候选 ID。
- archive_ref：最终入库时保存研究记录的持久引用。

`language_context` 必填：mode 为 single 或 mixed，targets 为非空去重语言 ID 列表，selection_basis 说明用户要求、上下文或默认的依据；toolchains 为每种目标语言提供 language、version、toolchain、platform。版本与环境按实际选择填写，不能只写 latest。single 恰好一种，mixed 至少两种。本套每种目标语言均须实际出现在题目中，每题只能采用已选择的目标语言；配置不改变评分或难度配比。

每个 question 项含：

```
{
  "id": "批次唯一题号",
  "title": "题目标题",
  "level": "basic 或 advanced",
  "implementation_languages": ["cpp"],
  "task_type": "build",
  "difficulty": {"modeling": 3, "algorithm": 2, "design": 2, "debugging": 2, "prerequisites": ["目标语言基础"], "learning_goals": ["具体学习目标"], "estimated_minutes": 120, "rationale": "具体难点", "calibration_basis": "初始估计，待真实完成数据校准"},
  "domain_tags": ["canonical-domain"],
  "concept_tags": ["canonical-concept"],
  "artifact_tags": ["canonical-output"],
  "engineering_tags": ["canonical-practice"],
  "candidate_ids": ["比较过的候选一", "独立候选二"],
  "source_review_ids": ["实际采用且已经合格的外部评估ID"],
  "cross_language_adaptations": [],
  "novelty_note": "相对最相似旧题，具体新增的约束和学习价值",
  "reference_review_id": "最终参考实现复评ID，草案时可省略"
}
```

`source_language_targets` 是来源 ID 到实际采用语言列表的映射。单语言题省略时默认全部来源用于该语言；多语言题必须显式填写，如 `{"go-source": ["go"], "ts-source": ["typescript"]}`。键与实际采用来源完全对应，值只能含本题语言，合起来覆盖本题全部语言，不能用错配掩盖移植。

`cross_language_adaptations` 为可选列表。同语言采用可留空；若来源源码语言未覆盖上述映射指定的采用语言，逐来源填 source_review_id、target_languages（映射中该来源未覆盖的语言）、semantic_risks 和 verification_plan。最终参考实现评估的 source.languages 必须与本题 implementation_languages 一致，并含逐语言实际测试证据。只有计划说明不足以替代运行。

`assets/question-template.json` 提供难度画像空模板。若用旧标签的新组合或约束深化计入广度，增加 `novelty_evidence`，格式与审阅要求见 [调研与多样性规则](research-diversity.md)；只填写 novelty_note 不会自动算作新覆盖。

先 `check-plan plan.json`，通过后才能编写完整内容；生成、测试、复评并入库参考实现后，运行 `check-plan plan.json --final`。计划检查不自动写入历史。

完成文件保存，填 `artifact`（至少包含实际返回的 library_file_id 或已验证 url）、research.archive_ref 和 validation 中四项实际结果，再运行 `record-batch plan.json`。它验证最终准入与交付状态后写入题库，同一批次不能重复添加。

脚本在 Linux/WSL 执行；写入使用锁和临时文件原子替换。拒绝或异常不会写入半份结果。出现历史指纹变化，重读题库并重新检查计划。保留锁文件的 inode，不手动删除正在使用的锁；它不纳入技能保存。

## 持久化规则

命令成功只表示本地索引已修改。继续按 skill-creator 的技能保存规则保存本技能，远端验证成功后才称“已入库”。原始测试日志与源代码可放在持久文件档案，索引留精简说明和引用，避免把庞大依赖放进技能。

题库结构版本为 3；2 版历史保留，不伪造执行档案或补齐通过标记。历史记录仅在有真实材料依据时补 implementation_languages；不升级 legacy_unreviewed 的评分状态。批次保存 language_context，stats 单独汇报语言覆盖及缺语言历史数量，语言不进入四维多样性公式。脚本不自动推测或迁移外部旧题库，未知字段先人工核实。

不要把合成测试评估、空模板、未经核实的旧题或搜索候选伪装成合格来源。脚本核验数据结构、阈值、快照与日志的一致性和可重算的用例结果，仍无法识别整套伪造记录或无效断言；真实性由执行者逐项核实。
