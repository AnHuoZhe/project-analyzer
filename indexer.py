"""Markdown project index."""
from pathlib import Path
from typing import Any

HEADER = "| repo_key | 项目名 | 类型 | 标签 | 分析日期 | 相关性 | 报告路径 |"
SEPARATOR = "| --- | --- | --- | --- | --- | --- | --- |"
COLUMNS = (
    "repo_key",
    "project_name",
    "project_type",
    "tags",
    "analysis_date",
    "relevance",
    "report_path",
)


def _empty_text() -> str:
    return f"{HEADER}\n{SEPARATOR}\n"


def _split_row(line: str) -> list[str]:
    return [part.strip() for part in line.strip().strip("|").split("|")]


def _read_entries(index_path: Path | str) -> list[dict[str, str]]:
    path = Path(index_path)
    if not path.exists():
        return []

    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        if line.strip() in {HEADER, SEPARATOR}:
            continue
        parts = _split_row(line)
        if len(parts) != len(COLUMNS):
            continue
        entries.append(dict(zip(COLUMNS, parts)))
    return entries


def _format_entry(entry: dict[str, Any]) -> str:
    tags = entry.get("tags", [])
    if isinstance(tags, list):
        tags_text = ",".join(str(tag) for tag in tags)
    else:
        tags_text = str(tags)

    values = [
        entry.get("repo_key", ""),
        entry.get("project_name", ""),
        entry.get("project_type", ""),
        tags_text,
        entry.get("analysis_date", ""),
        entry.get("relevance", ""),
        entry.get("report_path", ""),
    ]
    return "| " + " | ".join(str(value) for value in values) + " |"


def query_index(index_path: Path | str, repo_key: str) -> dict[str, Any]:
    for entry in _read_entries(index_path):
        if entry.get("repo_key") == repo_key:
            return {
                "schema_version": 1,
                "ok": True,
                "stage": "indexer_query",
                "found": True,
                "entry": entry,
            }

    return {
        "schema_version": 1,
        "ok": True,
        "stage": "indexer_query",
        "found": False,
        "entry": None,
    }


def update_index(index_path: Path | str, entry: dict[str, Any]) -> dict[str, Any]:
    path = Path(index_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    repo_key = str(entry.get("repo_key", ""))
    entries = [existing for existing in _read_entries(path) if existing.get("repo_key") != repo_key]
    entries.append(
        {
            "repo_key": repo_key,
            "project_name": entry.get("project_name", ""),
            "project_type": entry.get("project_type", ""),
            "tags": entry.get("tags", []),
            "analysis_date": entry.get("analysis_date", ""),
            "relevance": entry.get("relevance", ""),
            "report_path": entry.get("report_path", ""),
        }
    )

    text = _empty_text() + "\n".join(_format_entry(item) for item in entries) + "\n"
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(text, encoding="utf-8")
    temp_path.replace(path)

    return {
        "schema_version": 1,
        "ok": True,
        "stage": "indexer_update",
        "repo_key": repo_key,
        "updated": True,
    }
