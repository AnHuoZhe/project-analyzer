"""Perspective 4A: dialectical synthesis."""
import logging
from typing import Any, Callable

LOGGER = logging.getLogger(__name__)

REQUIRED_RESULTS = ("perspective1", "perspective2", "perspective3", "perspective4b")


def _invalid_input(message: str, repo_key: Any = None) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "ok": False,
        "stage": "perspective4a",
        "repo_key": repo_key,
        "error_code": "PERSPECTIVE4A_INPUT_INVALID",
        "message": message,
        "recoverable": False,
    }


def analyze_dialectic(
    results: dict[str, dict[str, Any]],
    client: Callable[[str], str],
) -> dict[str, Any]:
    for name in REQUIRED_RESULTS:
        if name not in results:
            return _invalid_input(f"missing {name}")
        if results[name].get("ok") is not True:
            return _invalid_input(f"failed prerequisite {name}", results[name].get("repo_key"))

    repo_key = results["perspective1"].get("repo_key")

    try:
        prompt = (
            "你是唯物辩证法分析器。基于四个前序 JSON 结果，分析这个项目由什么核心矛盾推动，"
            "包括主要矛盾、次要矛盾、矛盾如何塑造架构选择、哪些裂隙来自这些矛盾。\n"
            f"项目：{repo_key}\n"
            f"视角1：{results['perspective1'].get('content', '')}\n"
            f"视角2：{results['perspective2'].get('content', '')}\n"
            f"视角3：{results['perspective3'].get('content', '')}\n"
            f"视角4B：{results['perspective4b'].get('content', '')}"
        )
        content = client(prompt)
        LOGGER.info("已生成辩证法分析：%s", repo_key)
        return {
            "schema_version": 1,
            "ok": True,
            "stage": "perspective4a",
            "repo_key": repo_key,
            "content": content,
        }
    except Exception as error:
        return {
            "schema_version": 1,
            "ok": False,
            "stage": "perspective4a",
            "repo_key": repo_key,
            "error_code": "PERSPECTIVE4A_FAILED",
            "message": str(error),
            "recoverable": True,
        }
