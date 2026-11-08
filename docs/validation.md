# 整理版验证记录

验证日期：2026-11-04。验证对象为本仓库的工具、模板、相对目录与使用命令，不是网上项目认证。

本次实际环境：Python 3.12.14、Node.js 24.22.1、g++ 13.3.0，Linux。

## 实际结果

| 检查 | 结果 |
| --- | --- |
| 整套 unittest 回归 | 68 项通过，0 失败，0 跳过，10.986 秒 |
| 准入与训练计划规则 | 39 项通过 |
| 执行、证据、评分与打包 | 19 项通过 |
| 作业逐行批改与学习记录 | 10 项通过 |
| 基础 5 / 进阶 10 的配比命令 | 正确返回总数 15，无取整 |
| quickstart 中 Python 样本 run / verify | 12/12 用例通过，无跳过 |
| 样本的 learner 反馈 | 成功生成报告，未审阅的九维总分保持 null |
| JSON、文档相对链接、个人定位符检查 | 通过 |
| 原始工作流与核心代码对照 | 一致；仅分发版历史索引移除个人定位符 |

## 复现

在仓库根目录运行：

```bash
python3 -B -m unittest discover \
  -s skills/build-project-training/scripts \
  -p 'test_*.py' -v
```

运行 [quickstart](quickstart.md) 的配比与执行器样本命令可复核文档中的路径和工具衔接。重复运行时换一个新的输出目录。

GitHub Actions 配置已提供，使用官方 [checkout](https://github.com/actions/checkout) 和 [setup-python](https://github.com/actions/setup-python) 的文档版本。仓库尚未上传时不能声称 Actions 已通过；上传后以实际运行结果为准。

## 适用范围

本地回归实际运行 Python、Node.js JavaScript、g++ C++17 以及 Python 调用 JavaScript 的协作样本；其他语言保留适配规则，仍需对应工具链实测。基础工具为 Python 标准库；Linux/WSL 用于持久记录的文件锁。

自动检查验证分数计算、准入约束、执行档案一致性、报告结构和逐行覆盖，不验证 AI 所有语义判断。验证样本没有加入合格来源库，也没有作为学生真实学习记录保存。详细历史范围见技能内 [validation-status.md](../skills/build-project-training/references/validation-status.md)。

## 2026-11-08 CoderTrail 完整项目包

在保持核心 Skill、规则、模板与程序字节不变的情况下，合入完整 README，以 CoderTrail 为项目展示名称。技能标识与路径仍为 build-project-training，便于使用现有装载方式和命令。

本次在 Linux、Python 3.12.14、Node.js 24.22.1、g++ 13.3.0 环境重新执行完整回归：68 项通过，0 失败，0 跳过，耗时 11.271 秒。JSON、文档相对链接、文件完整性及个人定位符检查通过。

压缩包保留全部源码、测试、模板、历史主题索引和使用文档，排除工作目录、缓存、锁文件与本地配置。本次打包清单见根目录 PACKAGE_MANIFEST.json；清单记录其余交付文件的 SHA-256，清单自身不参与递归摘要。打包后的 CRC 和各文件摘要均已核验。运行环境、模型服务和工具链需由使用者自行提供。
