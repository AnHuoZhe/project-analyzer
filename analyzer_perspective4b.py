"""Perspective 4B: hidden risk and gap analysis."""
import logging
from typing import Any, Callable

LOGGER = logging.getLogger(__name__)

FIVE_CUTS = ("数据流", "失败模式", "状态", "分层", "运维隐患")


def analyze_hidden_risks(
    profile: dict[str, Any],
    client: Callable[[str], str],
) -> dict[str, Any]:
    repo_key = profile.get("repo_key")

    try:
        prompt = (
            "你是代码架构裂隙分析器。请只基于扫描结果判断，不编造未出现的实现。\n"
            "用五层切口分析项目：数据流、失败模式、状态、分层、运维隐患。\n"
            "每层输出：观察、潜在裂隙、影响、验证方法、优先级。\n"
            f"项目：{repo_key}\n"
            f"README：{profile.get('readme_excerpt', '')}\n"
            f"目录：{profile.get('tree', [])}\n"
            f"关键文件：{profile.get('key_files', [])}"
        )
        content = client(prompt)
        LOGGER.info("已生成裂隙分析：%s", repo_key)
        return {
            "schema_version": 1,
            "ok": True,
            "stage": "perspective4b",
            "repo_key": repo_key,
            "content": content,
        }
    except Exception as error:
        return {
            "schema_version": 1,
            "ok": False,
            "stage": "perspective4b",
            "repo_key": repo_key,
            "error_code": "PERSPECTIVE4B_FAILED",
            "message": str(error),
            "recoverable": True,
        }
