"""Perspective 5: personal relevance scoring."""
import logging
from typing import Any, Callable

LOGGER = logging.getLogger(__name__)

REQUIRED_RESULTS = (
    "perspective1",
    "perspective2",
    "perspective3",
    "perspective4b",
    "perspective4a",
)


def _repo_key_from(results: dict[str, dict[str, Any]]) -> Any:
    for result in results.values():
        if isinstance(result, dict) and result.get("repo_key"):
            return result.get("repo_key")
    return None


def _invalid_input(message: str, repo_key: Any) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "ok": False,
        "stage": "perspective5",
        "repo_key": repo_key,
        "error_code": "PERSPECTIVE5_INPUT_INVALID",
        "message": message,
        "recoverable": False,
    }


def _score(results: dict[str, dict[str, Any]], user_profile: str) -> int:
    text = " ".join(str(result.get("content", "")) for result in results.values()).lower()
    profile = user_profile.lower()
    score = 35

    if "agent" in text or "llm" in text:
        score += 20
    if "python" in text and "python" in profile:
        score += 15
    if "可复用" in text or "模式" in text or "tool" in text or "工具" in text:
        score += 15
    if "学习" in profile and ("架构" in text or "architecture" in text):
        score += 10

    return max(0, min(100, score))


def score_relevance(
    results: dict[str, dict[str, Any]],
    user_profile: str,
    client: Callable[[str], str],
) -> dict[str, Any]:
    repo_key = _repo_key_from(results)

    for name in REQUIRED_RESULTS:
        if name not in results:
            return _invalid_input(f"missing {name}", repo_key)
        if results[name].get("ok") is not True:
            return _invalid_input(f"failed prerequisite {name}", results[name].get("repo_key", repo_key))

    repo_key = results["perspective1"].get("repo_key", repo_key)

    try:
        prompt = (
            "你是个人适用性分析器。基于前序分析和用户画像，按四个固定维度判断项目是否值得深入："
            "技术栈熟悉度、现有项目关联度、学习阶段匹配度、可直接复用项。\n"
            "输出四维度逐项结论和综合建议。\n"
            f"用户画像：{user_profile}\n"
            f"项目：{repo_key}\n"
            f"视角1：{results['perspective1'].get('content', '')}\n"
            f"视角2：{results['perspective2'].get('content', '')}\n"
            f"视角3：{results['perspective3'].get('content', '')}\n"
            f"视角4B：{results['perspective4b'].get('content', '')}\n"
            f"视角4A：{results['perspective4a'].get('content', '')}"
        )
        content = client(prompt)
        relevance_score = _score(results, user_profile)
        LOGGER.info("已生成适用性分析：%s score=%s", repo_key, relevance_score)
        return {
            "schema_version": 1,
            "ok": True,
            "stage": "perspective5",
            "repo_key": repo_key,
            "content": content,
            "relevance_score": relevance_score,
        }
    except Exception as error:
        return {
            "schema_version": 1,
            "ok": False,
            "stage": "perspective5",
            "repo_key": repo_key,
            "error_code": "PERSPECTIVE5_FAILED",
            "message": str(error),
            "recoverable": True,
        }
