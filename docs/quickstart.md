# 使用与命令行

## 1. 环境与路径

在 Linux 或 WSL 中进入本仓库根目录。工具使用 Python 3.10+ 标准库，目标项目需要自己的运行时与编译器。Node.js 与 g++ 用于现有跨语言验证样本。

```bash
SKILL_DIR="$PWD/skills/build-project-training"
python3 --version
python3 -B "$SKILL_DIR/scripts/project_grader.py" --help
python3 -B "$SKILL_DIR/scripts/curate_bank.py" --help
mkdir -p work
```

work 用于本次研究、执行档案与批改报告，已由仓库忽略。输出目录必须是尚不存在的新目录，且放在被测项目目录之外。

## 2. 计算题目配比

```bash
python3 -B "$SKILL_DIR/scripts/curate_bank.py" mix
python3 -B "$SKILL_DIR/scripts/curate_bank.py" mix \
  --counts 5 10 --basis '用户要求5道基础、10道进阶'
python3 -B "$SKILL_DIR/scripts/curate_bank.py" mix \
  --ratio 2:3 --basis '用户要求基础与进阶为2比3'
python3 -B "$SKILL_DIR/scripts/curate_bank.py" mix \
  --basic-percent 50 --basis '用户要求基础占一半，接受并已说明取整'
```

默认总数 15；比例和百分比按既定规则取整。计算只返回配置，不生成训练题，也不替代前置调研、九维审阅及整套计划检查。

## 3. 跑通已有的执行器样本

以下使用现有验证样本确认环境与工具衔接，不是新增训练题或合格来源。

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

样本验收包含 12 个真实用例。未附九维审阅时，总分保持待评；查看 feedback 中的 grade.md 和 grade.json。保留整个 evidence 目录，不能只保存 execution.json。

实际项目从 [execution-manifest-template.json](../skills/build-project-training/assets/execution-manifest-template.json) 填写自己的明确验收合同。完整字段及退出码见 [评分程序](../skills/build-project-training/references/scoring-program.md)。

## 4. 提交作业并逐行批改

给 agent 提供原题要求、全部自写源码、已有测试和运行环境。它先固定原提交，审查命令并采集执行档案；低分、编译失败或用例失败仍可进入批改。缺少执行条件时保留静态反馈及待验证项。

复制 [homework-scope-template.json](../skills/build-project-training/assets/homework-scope-template.json) 到 work/scope.json，填写原题及文件范围；学生代码、学生测试与需要的配置均要清点，非学生文件逐项说明排除理由。随后针对实际作业的执行档案运行：

```bash
python3 -B "$SKILL_DIR/scripts/project_grader.py" prepare-homework \
  work/submission-evidence-01/execution.json \
  --scope work/scope.json --out work/homework-review.json
```

agent 阅读全部上下文后填写草稿的九维评分、每行作用、分数、理由、修改建议和共享问题。程序不会自动填充语义分数，也不能通过编造评语让记录变完整。

```bash
python3 -B "$SKILL_DIR/scripts/project_grader.py" check-homework \
  work/submission-evidence-01/execution.json --review work/homework-review.json

python3 -B "$SKILL_DIR/scripts/project_grader.py" review-homework \
  work/submission-evidence-01/execution.json --review work/homework-review.json \
  --out work/homework-feedback-01
```

命令返回 0 为批改记录完整，1 为仍有待评项，2 为配置或证据不合法。0 不代表作业达到 85 分。以下文件共同构成完整反馈：

| 文件 | 内容 |
| --- | --- |
| grade.md | 九维总评、真实验收结果、共享问题与优先行动 |
| line-review.md | 按原文件和行号完整逐行讲解 |
| grade.json | 机器可读总评与覆盖统计 |
| homework-review.json | 原文、证据引用与逐行评语记录 |

大作业按文件分段完成，再检查最终覆盖。修正版另存并重跑相同验收，原提交用于保留最初评分。详细规则见 [作业批改规范](../skills/build-project-training/references/homework-marking.md)。

## 5. 记录学习尝试

复制 [learning-observation-template.json](../skills/build-project-training/assets/learning-observation-template.json) 到 work/observation.json。填写实际耗时、提示和卡点，未知用 null。用实际生成的 grade.json 记录：

```bash
if [ ! -e work/learning-history.json ]; then
  cp "$SKILL_DIR/assets/learning-history.json" work/learning-history.json
fi

python3 -B "$SKILL_DIR/scripts/project_grader.py" record-attempt \
  work/homework-feedback-01/grade.json --observation work/observation.json \
  --history work/learning-history.json
```

history 指向独立的工作文件，避免将学生记录提交到分发仓库。失败尝试也保留，比较变化时需同题、同语言、同验收合同及同评分版本。

## 6. 维护训练题库

新套题按 SKILL.md 的调研 → 来源准入 → 多样性计划 → 实现复评 → 成品验证 → 记录批次执行。命令参数和 JSON 结构见 [记录规范](../skills/build-project-training/references/records.md)，不要把测试样本当作正式来源添加。
