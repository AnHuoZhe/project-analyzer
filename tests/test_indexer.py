from pathlib import Path

import indexer


def test_query_index_finds_existing_repo(tmp_path: Path) -> None:
    index_path = tmp_path / "index.md"
    index_path.write_text(
        "| repo_key | 项目名 | 类型 | 标签 | 分析日期 | 相关性 | 报告路径 |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        "| owner/demo | demo | agent_framework | agent,python | 2026-07-20 | 85 | reports/demo.md |\n",
        encoding="utf-8",
    )

    result = indexer.query_index(index_path, "owner/demo")

    assert result["ok"] is True
    assert result["found"] is True
    assert result["entry"]["repo_key"] == "owner/demo"
    assert result["entry"]["relevance"] == "85"


def test_update_index_replaces_existing_repo(tmp_path: Path) -> None:
    index_path = tmp_path / "index.md"
    indexer.update_index(
        index_path,
        {
            "repo_key": "owner/demo",
            "project_name": "demo",
            "project_type": "agent_framework",
            "tags": ["agent"],
            "analysis_date": "2026-07-19",
            "relevance": 70,
            "report_path": "reports/old.md",
        },
    )
    indexer.update_index(
        index_path,
        {
            "repo_key": "owner/demo",
            "project_name": "demo",
            "project_type": "agent_framework",
            "tags": ["agent", "python"],
            "analysis_date": "2026-07-20",
            "relevance": 85,
            "report_path": "reports/new.md",
        },
    )

    text = index_path.read_text(encoding="utf-8")
    assert text.count("owner/demo") == 1
    assert "reports/new.md" in text
    assert "reports/old.md" not in text
