from pathlib import Path

import scanner


def test_scan_project_builds_profile_from_readme_and_python_entry(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Demo Agent\nAn LLM agent project.", encoding="utf-8")
    (tmp_path / "main.py").write_text("print('hello')", encoding="utf-8")

    profile = scanner.scan_project(tmp_path, "owner/demo")

    assert profile["schema_version"] == 1
    assert profile["repo_key"] == "owner/demo"
    assert profile["project_type"] == "agent_framework"
    assert "Python" in profile["languages"]
    assert profile["entry_files"] == ["main.py"]


def test_scan_project_detects_common_non_python_languages(tmp_path: Path) -> None:
    (tmp_path / "index.ts").write_text("export {}", encoding="utf-8")
    (tmp_path / "main.go").write_text("package main", encoding="utf-8")

    profile = scanner.scan_project(tmp_path, "owner/polyglot")

    assert profile["languages"] == ["TypeScript", "Go"]


def test_scan_project_returns_error_envelope_for_missing_directory(tmp_path: Path) -> None:
    result = scanner.scan_project(tmp_path / "missing", "owner/missing")

    assert result["ok"] is False
    assert result["error_code"] == "SCAN_FAILED"


def test_scan_project_records_readme_truncation(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("x" * 12001, encoding="utf-8")

    profile = scanner.scan_project(tmp_path, "owner/large")

    assert "readme_truncated_12000" in profile["truncation_warnings"]
