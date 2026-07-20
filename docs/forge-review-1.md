# 审查报告 — 第1轮

## 必须改

1. **模块职责偏离需求** / architecture.md 模块职责表
   原因：需求定了10个模块，架构拆成11个——多了repository、analysis_runner、ranking、presentation、reporting、state_store，同时把perspective4a+5合并为synthesis、perspective3分类功能+indexer合并为knowledge_index。原本每个视角独立文件清晰可维护，合并后职责混杂。
   建议：保持10模块不变。repository合并到searcher（克隆本就是搜索阶段的事）。presentation和reporting合并到orchestrator（本就是编排器的交互和输出职责）。ranking逻辑并入orchestrator的排序阶段（纯代码逻辑不需要独立模块）。state_store砍掉（不需要SQLite，索引是markdown文件）。

2. **六维度裁掉了成本控制和评估** / architecture.md "中方案裁减范围"段
   原因：写"不包含成本控制体系和离线评估平台"。但需求明确要求视角3逐维度覆盖全部六个维度。成本控制不是说必须有运行时监控系统，是分析项目本身在这个维度上做了什么设计决策。评估同理——不是说必须建评估平台，是说项目有没有评估机制。
   建议：六维度全保留，上下文工程/记忆系统/工具调用/可靠性/成本控制/评估一个不少。去掉这个裁减说明。

3. **多加SQLite** / architecture.md 多处提到SQLite
   原因：需求没要求SQLite。索引就是个markdown文件（E:\work\word\study\word\项目分析索引.md），运行状态不需要跨进程持久化。加SQLite引入了不必要的依赖和复杂度。
   建议：砍掉SQLite。索引读写用纯文本（pathlib读markdown）。运行状态存内存中的dict，不需要落盘。

## 已确认可去（非问题）

- B站获取方式已验证，可以去掉"需在实现前验证"的标注。格式确认为：空间页拿BV号 → 视频简介正则提取github.com链接。
- 用户画像已定义在需求文档中，不需要再"定义持久化来源"。
- 分类库路径已确认：C:\Users\Luo\AppData\Local\hermes\profiles\learning\skills\thinking-partner\six-dimensions-analyzer\references\classification.md

## 保留的部分（好的设计）

- ProjectProfile共享扫描结果——一次扫描全部视角复用
- subprocess隔离分析器——互不import，干净
- 单项目失败不阻断其他——容错正确
- Git代理finally清理——不会残留
- DeepSeek超时120秒+重试一次

## 自问段

- 模块数问题是过度工程还是正当抽象？repository独立出来有道理——但现阶段10个模块够用，多了反而维护乱。等真正需要拆分时再拆。
- SQLite有必要吗？没有。索引量不会超过几百条，markdown文件搜索和读写完全够。
