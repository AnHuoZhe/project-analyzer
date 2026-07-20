# 项目分析 Agent 架构

## 1. 产品概述

这是一个纯命令行 Python 应用。执行 `python orchestrator.py` 后，应用从 B 站 UP 主“大雄AI实战”（UID `383325863`）最新 GitHub 热榜视频中提取、去重并克隆最多十个仓库；对未分析的项目扫描代码、完成五个视角分析，按个人相关性排序、逐项展示，并为每个成功分析项目无条件保存完整 Markdown 报告。

**选定方案：中方案，交互深度：简单。** 保留需求规定的十个业务模块、dict/JSON 与 subprocess 解耦、内存 dict 运行状态、本地 Markdown 分类库和项目索引。禁止新增 SQLite、独立 `repository`、`ranking`、`presentation`、`reporting` 或 `state_store` 模块；排序、CLI 展示、报告与恢复编排均属于 `orchestrator.py`。

### 范围、假设与裁减

- 固定外部路径由现有配置读取：下载目录、报告目录、项目索引 `E:\\work\\word\\study\\word\\项目分析索引.md`、六维度分类库 `C:\\Users\\Luo\\AppData\\Local\\hermes\\profiles\\learning\\skills\\thinking-partner\\six-dimensions-analyzer\\references\\classification.md`，以及 `hermes/.env`。
- DeepSeek 使用 `deepseek-chat`；每次调用 120 秒，失败只重试一次。网络请求和 Git 克隆使用 `http://127.0.0.1:7890`；Git 操作结束必须恢复原全局代理值或清除本次设置。
- 中方案展开数据流、失败模式、状态、分层、上下文工程、记忆系统、工具调用和可靠性；不做服务拆分、分布式队列、跨运行状态服务、SQLite 或监控平台。
- 已确认发现方式为“空间页取最新 BV 号 → 视频简介正则提取 `github.com` 链接”。规范仓库主键为 `repo_key = lowercase(owner + "/" + repo)`：去除协议、`www.`、末尾 `/`、`.git`、片段与查询参数后，仅接受 GitHub 两段路径；规范 URL 为 `https://github.com/{repo_key}`。

## 2. 架构设计

### 十模块职责与边界

| 模块 | 输入 | 输出 | 负责 / 不负责 |
| --- | --- | --- | --- |
| `searcher.py` | UID、空间/视频 URL、下载目录 | 最多十个规范仓库结果 | 发现、规范化、去重、克隆；不判断分析历史。 |
| `scanner.py` | 本地仓库路径 | `ProjectProfile` | README、目录树、关键文件与类型识别；不调用模型。 |
| `analyzer_perspective1.py` | `ProjectProfile` | 概览 | “是什么、解决什么、谁使用”。 |
| `analyzer_perspective2.py` | `ProjectProfile` | 架构分析 | 模块、前后端、数据流与核心实现。 |
| `analyzer_perspective3.py` | `ProjectProfile`、六维度尺子 | 固定六维度工程评估 | 仅生成机器可读评估与分类发现；不直接写文件。 |
| `analyzer_perspective4b.py` | `ProjectProfile` | 裂隙分析 | 数据流、失败模式、状态、分层、运维隐患。 |
| `analyzer_perspective4a.py` | 前四个视角 JSON | 辩证法分析 | 仅消费 JSON，不 import 其他 analyzer。 |
| `analyzer_perspective5.py` | 全部前序结果、固定用户画像 | 适用性与相关性分 | 产生排序输入和建议。 |
| `indexer.py` | 查询条件或索引更新载荷 | 查询命中或写入结果 | 单一 Markdown 读写者；不扫描、不排序、不生成报告。 |
| `orchestrator.py` | 配置、模块 JSON、CLI 输入 | 排序展示、报告 | 主入口、内存状态、subprocess 调度、排序、报告和恢复编排。 |

`orchestrator.py` 先调用 `searcher.py`，对每个候选仓库先调用 `indexer.py query`，只有未命中已分析同类的候选才会 `scanner.py` 并进入四路并行；随后 4A、5、索引、报告依次执行。所有 analyzer 以 stdin 或一个具名 JSON 输入文件接收数据、以 stdout **或**一个具名 JSON 输出文件返回结果（一次调用只选一种），不得互相 import。`ProjectProfile` 是共享且截断的上下文，避免重复扫描与无边界模型输入。

`ProjectProfile` 固定为版本化 JSON 对象。必填字段为 `schema_version`（整数，当前 `1`）、`repo_key`（字符串）、`repo_path`（字符串）、`project_type`（字符串枚举）、`languages`（字符串数组）、`tags`（字符串数组）、`readme_excerpt`（字符串）、`tree`（字符串数组）、`key_files`（对象数组）和 `truncation_warnings`（对象数组）；可选字段为 `frameworks`（字符串数组）与 `entry_files`（字符串数组）。`project_type` 只能是 `agent_framework`、`frontend_library`、`cli_tool`、`content_platform`、`backend_service`、`mobile`、`other` 之一。`readme_excerpt` 最多 12,000 字符；目录树最多 300 条；关键文件最多 20 个、每个对象含 `path`、`excerpt`（最多 8,000 字符）和可选 `language`。每个 `truncation_warnings` 项固定为 `{ "field": "字段名", "original_count_or_chars": 123, "retained_count_or_chars": 45, "reason": "size_limit" }`。`scanner.py` 在输出前校验必填字段、类型和上限；不满足时返回 `SCAN_PROFILE_INVALID`，不启动 analyzer。

### 分层、状态与历史判定

```text
发现/克隆：searcher
                  ↓
历史查询：indexer query ──命中──> skipped_analyzed（终端列出；不写新报告）
                  ↓ 未命中
扫描：scanner → 并行：P1 / P2 / P3 / P4B → 串行：P4A → P5
                  ↓
索引与分类：indexer update → 报告原子写入：orchestrator → CLI 只读展示
```

单项目状态仅为 `orchestrator.py` 内存 dict：`discovered → cloning → history_checked → scanned → parallel_analyzed → dialectic_analyzed → fitness_analyzed → indexed → reported`。历史命中转换为 `skipped_analyzed`，记录 `matched_repo_keys`、`same_kind_rule` 和 `skip_reason`，不进入扫描/模型调用、不追加索引、不生成新报告；终端摘要单独列出。其他阶段失败转为 `failed`，保留 `failed_stage`、`error_code`、`message` 和可恢复信息，且不阻塞其他项目。

同类判定由 `indexer.py` 统一实施：先按相同 `repo_key` 精确命中；否则，当已索引项目与候选的规范化 `project_type` 相同，且规范化标签集合有至少一个交集时为同类。候选在扫描前尚无可靠类型/标签，查询只执行精确 `repo_key` 命中；扫描后、并行分析前以 `ProjectProfile.project_type` 和扫描标签执行同类查询。两次查询均命中即跳过，第二次命中仍未调用任何 analyzer。缺少类型或标签时只做精确匹配，绝不猜测同类。

### 视角 3 与文件记忆契约

`analyzer_perspective3.py` 成功结果的 `content` 必须严格包含以下六个键：`context_engineering`、`memory_system`、`tool_calling`、`reliability`、`cost_control`、`evaluation`。每一维均为：

```json
{
  "applicable": true,
  "judgement": "good",
  "evidence": ["可定位的文件或行为证据"],
  "recommendations": ["可操作建议"]
}
```

`applicable` 为布尔值；`judgement` 只能是 `good`、`bad` 或 `not_applicable`，且仅当 `applicable=false` 时使用 `not_applicable`；`evidence` 和 `recommendations` 均为字符串数组。顶层另有必填 `classification_findings` 数组，每项为 `{ "dimension": "六个固定键之一", "label": "稳定分类标签", "finding": "简短发现", "evidence": ["..."] }`。缺键、额外维度、枚举非法或证据类型错误均为 `PERSPECTIVE3_SCHEMA_INVALID`，不进入索引。

`orchestrator.py` 将已校验的 P3 结果、`repo_key`、类型、标签、分析日期、相关性和将要写入的报告路径封装为 `IndexUpdateRequest` JSON，通过 `indexer.py update` 子进程传入；P3 从不直接写分类库。项目索引的幂等键是 `repo_key`，分类库的幂等键是 `repo_key + ":" + dimension + ":" + label`；重复运行更新既有条目而非追加重复条目。

## 3. 数据流

### 正常路径样例

输入为视频中的 `https://github.com/acme/agent-kit`。`searcher.py` 规范化为 `repo_key=acme/agent-kit`，克隆到固定下载目录；`orchestrator.py` 创建内存状态并先执行精确历史查询。若未命中，`scanner.py` 生成含 `schema_version`、`repo_key`、`project_type`、`tags`、README 摘要、前三层目录、关键文件和 `truncation_warnings` 的 `ProjectProfile`；随后执行第二次同类查询。仍未命中才启动 P1、P2、P3、P4B 并行，P4A、P5 串行。

P3 返回六个完整维度和 `classification_findings`；P5 返回 `relevance_score`。`orchestrator.py` 构造更新载荷并调用 `indexer.py update`，索引成功后状态为 `indexed`。接着无条件渲染完整五视角 Markdown 到报告临时文件，原子替换目标文件成功后才转换为 `reported`。所有项目处理完毕后按相关性排序；CLI 概览或“展开”只读取 `reported` 项的已存在报告，绝不把报告写入延迟到用户操作。

### Markdown 格式与原子更新顺序

项目索引使用每个仓库一个稳定区块，以 HTML 锚点承载幂等键，便于无数据库解析和替换：

```markdown
<!-- project:acme/agent-kit -->
## acme/agent-kit
- repo_key: `acme/agent-kit`
- analyzed_at: `2026-07-20T00:00:00Z`
- project_type: `agent`
- tags: `python`, `llm`
- relevance_score: `87`
- report_path: `固定报告路径`
- dimensions: `context_engineering:good`, `memory_system:not_applicable`, ...
<!-- /project:acme/agent-kit -->
```

分类库使用同样可替换的 `<!-- classification:{repo_key}:{dimension}:{label} -->` 区块，包含仓库键、维度、标签、发现、证据与日期；同键以新内容整体替换。一次 `indexer.py update` 先在内存中计算分类库和项目索引的新全文，分别写入同目录临时文件、`flush`/`fsync`，然后**先原子替换分类库、再原子替换项目索引**；仅两者替换都成功才返回 `updated=true`。单写入者为当前 `orchestrator.py` 进程；并发运行须以索引锁文件取得排他锁，不能取得锁返回 `INDEX_LOCKED`，不得并发改写。

每次 `indexer.py update` 生成 `update_id = {run_id}:{repo_key}`，并在两个目标文件的对应区块中写入相同的 `<!-- pending-update:{update_id} -->` 标记；第二次原子替换成功后，将两个标记替换为 `<!-- committed-update:{update_id} -->`。启动、重试或获取索引锁后，`indexer.py` 检查同一 `update_id`：若两文件都已 committed 则直接幂等成功；若任一文件为 pending 或仅一侧存在，则从本次保留的 `IndexUpdateRequest` 中重新计算并同时覆盖两个区块，再标记 committed；缺少恢复输入则返回 `INDEX_RECOVERY_REQUIRED`，保持锁外可诊断且不进入报告阶段。此标记仅服务文件恢复，不是数据库或额外状态模块。

报告写入在索引成功后执行：先写 `{report_path}.tmp-{run_id}`、`flush`/`fsync`，再以原子替换发布为最终 Markdown。临时文件只在成功替换后删除；启动时或项目重试前，`orchestrator.py` 删除属于该 `run_id` 的残留临时文件，保留并报告其他 run 的文件，避免误删未知工作。

### 部分成功恢复

- 分类库或项目索引任一替换失败：`indexer.py` 返回 `INDEX_WRITE_FAILED`、保留临时文件路径和已替换目标；项目停在 `fitness_analyzed`/失败状态，报告不写。下次运行以同一幂等键重新计算并完成覆盖，禁止当作 `indexed`。
- 索引成功但报告替换失败：状态保留为 `indexed` 并标记 `REPORT_WRITE_FAILED`、最终报告路径和临时文件路径；索引条目已含该报告路径。下次启动或对同一 `repo_key` 重跑时，先尝试用保留的完整内存/中间 JSON 重新渲染报告；成功即转换 `indexed → reported`，不重复追加索引。CLI 显示“报告待恢复”，不允许展开。
- 最终报告已存在时原子替换允许覆盖同一 `repo_key` 的旧报告；任何未完成临时文件均不是可展示报告。

## 4. 接口定义

所有成功/失败结果采用版本化 JSON envelope：成功为 `{ "schema_version": 1, "ok": true, "stage": "...", "repo_key": "...", "content": {} }`；失败为 `{ "schema_version": 1, "ok": false, "stage": "...", "repo_key": "...", "error_code": "...", "message": "...", "recoverable": true }`。`repo_key` 对非仓库级发现错误可为 `null`。中间 JSON 置于本运行专属目录，成功后可清理，失败或 `indexed` 报告恢复时保留。

| 接口 | 输入 | 成功输出 | 关键失败 |
| --- | --- | --- | --- |
| `search_projects` | UID、下载根目录 | `{repo_key,url,path,action}` 数组 | `VIDEO_FETCH_FAILED`、`GIT_CLONE_FAILED` |
| `scan_project` | 路径、`repo_key` | 版本化 `ProjectProfile` | `SCAN_FAILED` |
| `indexer query` | `repo_key`，可选 `project_type,tags` | `{exact_matches,same_kind_matches,rule}` | `INDEX_READ_FAILED`、`INDEX_LOCKED` |
| `run_analyzer` | JSON 输入路径、分析器名 | 对应视角 envelope | `ANALYZER_FAILED`、`PERSPECTIVE3_SCHEMA_INVALID` |
| `indexer update` | `IndexUpdateRequest`（含 P3） | `{updated:true,index_path,classification_path}` | `INDEX_WRITE_FAILED` |
| `write_report` | 全部五视角、报告路径 | `{report_path,atomic:true}` | `REPORT_WRITE_FAILED` |

## 5. 失败模式

| 场景 | 处理 | 用户可见结果 |
| --- | --- | --- |
| B 站不可用、URL 无效或不足十个 | 记录来源与原因，按有效项目继续 | 有效数与发现错误摘要。 |
| 历史精确/同类命中 | 状态设为 `skipped_analyzed`，不扫描、不调用模型、不写新报告 | 显示命中的仓库和同类规则。 |
| Git 克隆或代理失败 | 单项目失败；恢复原代理设置，恢复失败另记告警 | 不影响其余仓库。 |
| 模型超时、无效 JSON 或 P3 schema 不合法 | 120 秒且仅重试一次；项目停在当前阶段 | 指出视角和可定位错误。 |
| 索引锁、分类库/索引写入失败 | 单写入者和临时文件；不进入报告阶段 | 指出路径、锁/临时文件及恢复方式。 |
| 索引成功、报告失败 | 保持 `indexed`，保留恢复输入和临时文件 | 显示“报告待恢复”，不可展开。 |
| CLI 退出 | 停止调度新项目；已 `reported` 报告保持可用 | 汇总成功、跳过、待恢复与失败数。 |

## 6. 技术栈

- Python 3 CLI；标准库优先：`argparse`、`subprocess`、`json`、`pathlib`、`concurrent.futures`、`re`、`tempfile`、`os.replace`。
- `requests` 与 `BeautifulSoup` 获取 B 站页面；Git CLI 克隆，代理限制在受控临界区并恢复先前设置。
- DeepSeek `deepseek-chat`，从 `hermes/.env` 加载配置，统一 120 秒超时和一次重试。
- Markdown 是项目索引、分类库和报告的持久化格式；JSON 仅用于版本化模块契约与运行中间结果；不使用 SQLite。
