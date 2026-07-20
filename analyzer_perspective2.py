"""Perspective 2: architecture skeleton."""
import logging
from typing import Any, Callable

LOGGER = logging.getLogger(__name__)

def analyze_architecture(profile: dict[str, Any], client: Callable[[str], str]) -> dict[str, Any]:
    prompt = f"基于项目目录和关键文件，说明模块划分、数据流与核心实现。项目：{profile.get('repo_key','')}；目录：{profile.get('tree',[])}；文件：{profile.get('key_files',[])}"
    try:
        content = client(prompt)
        LOGGER.info("已生成架构骨架：%s", profile.get("repo_key"))
        return {"schema_version": 1, "ok": True, "stage": "perspective2", "repo_key": profile.get("repo_key"), "content": content}
    except Exception as error:
        return {"schema_version": 1, "ok": False, "stage": "perspective2", "repo_key": profile.get("repo_key"), "error_code": "PERSPECTIVE2_FAILED", "message": str(error), "recoverable": True}
