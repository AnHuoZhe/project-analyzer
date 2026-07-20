# Project Analyzer

每日自动抓取 GitHub Trending 前十项目，五视角深度分析，输出 Word 报告。

## 五个视角

1. **项目概览** — 是什么、解决什么、谁用
2. **架构骨架** — 模块划分、数据流、核心实现
3. **工程评估** — 六维度分析（上下文工程/记忆系统/工具调用/可靠性/成本控制/评估）
4. **方法论** — 唯物辩证法矛盾分析 + 架构裂隙分析
5. **适用性分析** — 技术栈匹配度、项目关联度、学习阶段匹配度、可复用项

## 使用方法

```bash
pip install -r requirements.txt
python orchestrator.py
```

输出到 `E:\work\word\study\word\`，Word 格式。

配置文件：`C:\Users\<用户名>\AppData\Local\hermes\.env`

```
DEEPSEEK_API_KEY=你的密钥
```

可选换用 Tokeness 中转站：
```
TOKENESS_API_KEY=你的Tokeness密钥
TOKENESS_BASE_URL=https://n.tokeness.io/v1/chat/completions
TOKENESS_MODEL=gpt-5.6-terra
```
