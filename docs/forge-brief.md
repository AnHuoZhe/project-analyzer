# 锻造简报

- 当前阶段：build（任务拆解）
- 方案规模：中方案
- 交互深度：简单
- 项目路径：E:\\work\\word\\study\\project-analyzer

## 用户需求

创建纯命令行 Python 项目：每天从 B 站 UP 主“大雄AI实战”（UID 383325863）的最新 GitHub 热榜视频提取前十个 GitHub 项目，克隆到本地；扫描代码后以五个视角分析，按用户相关性排序、逐项展示，并保存 Markdown 报告。按需求定义的 10 个模块实现，严格 TDD，Git 提交信息使用中文。

## 约束

- DeepSeek 配置来自 hermes/.env，使用 deepseek-chat；每次调用超时 120 秒，失败重试一次。
- 网络与 Git 克隆使用 http://127.0.0.1:7890 代理，并在操作后清除 Git 全局代理。
- 模块通过 dict/JSON 与 subprocess 解耦，analyzer 之间不得互相 import。
- 外部尺子、分类库、索引、项目下载目录与报告目录均按需求文档的固定路径访问。

## 已确认的功能范围

见 `docs/features.md`。

## 架构审查反馈（必须修复）

- 在扫描与并行分析前，`orchestrator.py` 必须调用 `indexer.py` 查询已分析同类项目；定义规范仓库主键、同类规则、跳过状态和报告策略。
- 为视角 3 定义固定六维度机器可读输出：每维适用性、好/不好、证据、建议，以及 `classification_findings`；规定它如何传给 `indexer.py`，并定义分类库、项目索引的幂等键、Markdown 格式与原子写入顺序。
- 将完整报告写入移动到 `indexed → reported` 的无条件状态转换；CLI 的展开只读取既有报告。定义报告写入失败、临时文件与索引/报告部分成功的可恢复处理。

## 保持不变的设计边界

- 必须保持需求规定的十个模块，不新增 SQLite、独立 repository/ranking/presentation/reporting/state_store 模块。
- 视角 3 继续覆盖全部六维度；运行状态仍为内存 dict。

## 第二轮审查建议（简单模式纳入修订）

- 在接口定义中补充 `ProjectProfile` 的版本化字段表、必填/可选字段、字段类型、扫描片段截断单位与上限，以及 `truncation_warnings` 最小结构。
- 为一次 `indexer.py update` 定义轻量提交标记或运行标识，说明启动/重试如何基于同一幂等键识别、重算或完成分类库与项目索引的部分提交；不得引入数据库或状态模块。

## 本次任务审查

- 审查类型：任务审查
- 输入：`docs/architecture.md`、`docs/tasks.json`
- 输出：`docs/task-review.md`
- 检查十模块覆盖、拓扑依赖、任务独立性与 schema。

## 任务审查修订（必须改及简单模式建议）

- 仅修订 `docs/tasks.json`，不得重写已批准架构。
- 将 `init_env` 定义为可在空项目中独立执行的引导任务：选定 Python 包管理/测试方案，创建依赖声明、测试配置、最小冒烟测试和基础目录，明确最小测试命令及 `output_files`。
- 定义所有 `test_result_path` JSON 的最小 schema：任务 ID、执行命令、状态、时间和失败摘要；`init_env` 也遵循。
