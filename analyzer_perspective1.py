"""Perspective 1: plain-language project overview."""
import logging
from typing import Any, Callable

LOGGER = logging.getLogger(__name__)

def analyze_profile(profile: dict[str, Any], client: Callable[[str], str]) -> dict[str, Any]:
    prompt = f"基于以下项目资料，用中文说明它是什么、解决什么问题、谁会使用。\n项目：{profile.get('repo_key', '')}\nREADME：{profile.get('readme_excerpt', '')}"
    try:
        content = client(prompt)
        LOGGER.info("已生成项目概览：%s", profile.get("repo_key"))
        return {"schema_version": 1, "ok": True, "stage": "perspective1", "repo_key": profile.get("repo_key"), "content": content}
    except Exception as error:
        LOGGER.error("项目概览生成失败：%s", error)
        return {"schema_version": 1, "ok": False, "stage": "perspective1", "repo_key": profile.get("repo_key"), "error_code": "PERSPECTIVE1_FAILED", "message": str(error), "recoverable": True}
