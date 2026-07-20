## 必须改

无。

## 建议改

- 问题描述：`search_projects` 尚未以模块级测试锁定 BV 缺失、视频简介获取失败，以及标准输入/输出入口的 JSON 输入错误三个 envelope 分支。
- 为什么：这些分支属于同一 discovery 数据流的可定位失败语义，后续调整时可能使契约回归。
- 修复方向：用注入 HTTP 获取器和 stdin/stdout mock，断言 `BVID_NOT_FOUND`、`VIDEO_FETCH_FAILED`、`SEARCH_INPUT_INVALID` 的完整版本化 JSON envelope。

- 问题描述：受限 worktree 的 `tmp_path` 写入/删除权限妨碍完整 pytest 的真实退出码记录。
- 为什么：日志已显示清理分支执行，但环境限制与代码回归需要可区分的证据。
- 修复方向：在可创建和删除临时目录的正常实现环境运行 `python -B -m pytest tests -q`，并将环境性权限失败与断言失败分开记录。

## 可忽略

无。

审查收敛记录：上轮三项必须改均已闭环；本轮未发现新的严重问题，建议数为 2，满足收敛条件。
