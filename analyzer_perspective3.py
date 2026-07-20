"""Perspective 3: Agent engineering dimensions."""
import logging
from typing import Any, Callable

LOGGER = logging.getLogger(__name__)

AGENT_PROJECT_TYPES = {"agent_framework", "llm_app", "agent_app"}
AGENT_KEYWORDS = ("agent", "llm", "large language model")
DIMENSIONS = (
    "context_engineering",
    "memory_system",
    "tool_calling",
    "reliability",
    "cost_control",
    "evaluation",
)
JUDGEMENTS = {"good", "bad", "not_applicable"}


def _is_agent_project(profile: dict[str, Any]) -> bool:
    project_type = str(profile.get("project_type", "")).lower()
    if project_type in AGENT_PROJECT_TYPES:
        return True

    readme = str(profile.get("readme_excerpt", "")).lower()
    return any(keyword in readme for keyword in AGENT_KEYWORDS)


def _schema_error(repo_key: Any, message: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "ok": False,
        "stage": "perspective3",
        "repo_key": repo_key,
        "error_code": "PERSPECTIVE3_SCHEMA_INVALID",
        "message": message,
        "recoverable": False,
    }


def _strings(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _validate_content(content: Any) -> str | None:
    if not isinstance(content, dict):
        return "content must be an object"
    if set(content) != set(DIMENSIONS):
        return "content must contain exactly six dimensions"

    for dimension, value in content.items():
        if not isinstance(value, dict):
            return f"{dimension} must be an object"
        applicable = value.get("applicable")
        judgement = value.get("judgement")
        if not isinstance(applicable, bool):
            return f"{dimension}.applicable must be boolean"
        if judgement not in JUDGEMENTS:
            return f"{dimension}.judgement is invalid"
        if applicable and judgement == "not_applicable":
            return f"{dimension}.judgement conflicts with applicable"
        if not applicable and judgement != "not_applicable":
            return f"{dimension}.judgement conflicts with not applicable"
        if not _strings(value.get("evidence")):
            return f"{dimension}.evidence must be string list"
        if not _strings(value.get("recommendations")):
            return f"{dimension}.recommendations must be string list"
    return None


def _validate_findings(findings: Any) -> str | None:
    if not isinstance(findings, list):
        return "classification_findings must be a list"
    for item in findings:
        if not isinstance(item, dict):
            return "classification finding must be an object"
        if item.get("dimension") not in DIMENSIONS:
            return "classification finding dimension is invalid"
        if not isinstance(item.get("label"), str):
            return "classification finding label must be string"
        if not isinstance(item.get("finding"), str):
            return "classification finding must be string"
        if not _strings(item.get("evidence")):
            return "classification finding evidence must be string list"
    return None


def analyze_engineering(
    profile: dict[str, Any],
    client: Callable[[str], str],
    ruler_text: str = "",
    classification_text: str = "",
) -> dict[str, Any]:
    repo_key = profile.get("repo_key")

    if not _is_agent_project(profile):
        LOGGER.info("非 Agent/LLM 项目跳过六维度分析：%s", repo_key)
        return {
            "schema_version": 1,
            "ok": True,
            "stage": "perspective3",
            "repo_key": repo_key,
            "content": "不适用",
            "classification_findings": [],
        }

    try:
        prompt = (
            "你是 Agent 工程评估器。只分析项目本身已经体现的工程设计，不假设未出现的能力。\n"
            "请逐项覆盖六个维度：上下文工程、记忆系统、工具调用、可靠性、成本控制、评估。\n"
            "每个维度输出：适用性、好/不好标注、证据、改进建议、分类归属。\n"
            f"项目：{repo_key}\n"
            f"README：{profile.get('readme_excerpt', '')}\n"
            f"目录：{profile.get('tree', [])}\n"
            f"关键文件：{profile.get('key_files', [])}\n"
            f"六维度尺子：{ruler_text}\n"
            f"分类库：{classification_text}"
        )
        raw = client(prompt)
        content = raw.get("content") if isinstance(raw, dict) else raw
        findings = raw.get("classification_findings", []) if isinstance(raw, dict) else []
        # Accept string output directly; only validate dict-structured responses
        if isinstance(content, str):
            pass  # string output accepted as-is
        else:
            content_error = _validate_content(content)
            if content_error:
                return _schema_error(repo_key, content_error)
            findings_error = _validate_findings(findings)
            if findings_error:
                return _schema_error(repo_key, findings_error)
        return {
            "schema_version": 1,
            "ok": True,
            "stage": "perspective3",
            "repo_key": repo_key,
            "content": content,
            "classification_findings": findings,
        }
    except Exception as error:
        return {
            "schema_version": 1,
            "ok": False,
            "stage": "perspective3",
            "repo_key": repo_key,
            "error_code": "PERSPECTIVE3_FAILED",
            "message": str(error),
            "recoverable": True,
        }
