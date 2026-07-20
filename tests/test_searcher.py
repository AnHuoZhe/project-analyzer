from pathlib import Path
import subprocess
from io import StringIO
import json

import searcher


def test_extract_latest_bvid_from_space_page() -> None:
    html = '<a href="//www.bilibili.com/video/BV1ab411c7xy">latest</a>'
    assert searcher.extract_latest_bvid(html) == "BV1ab411c7xy"


def test_extract_github_urls_deduplicates_and_keeps_order() -> None:
    description = "1、https://github.com/Owner/Repo\n2、https://github.com/Owner/Repo/\n3、https://github.com/next/tool"
    assert searcher.extract_github_urls(description) == [
        "https://github.com/Owner/Repo",
        "https://github.com/next/tool",
    ]


def test_normalize_repositories_filters_invalid_and_limits_to_ten() -> None:
    urls = [
        "https://github.com/Owner/Repo.git?x=1#part",
        "https://github.com/owner/repo/",
        "https://example.com/not-a-repo",
        *[f"https://github.com/acme/tool-{index}" for index in range(12)],
    ]
    repositories = searcher.normalize_repositories(urls)
    assert repositories[0] == {"repo_key": "owner/repo", "url": "https://github.com/owner/repo"}
    assert len(repositories) == 10


def test_clone_repository_restores_previous_proxy(monkeypatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], **_kwargs: object):
        calls.append(command)
        if command[-2:] == ["http.proxy", "--get"]:
            return type("Result", (), {"returncode": 0, "stdout": "http://old-proxy\n", "stderr": ""})()
        return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(searcher.subprocess, "run", fake_run)
    result = searcher.clone_repository(
        {"repo_key": "owner/repo", "url": "https://github.com/owner/repo"}, tmp_path
    )
    assert result["action"] == "cloned"
    assert ["git", "config", "--global", "http.proxy", searcher.PROXY_URL] in calls
    assert ["git", "config", "--global", "http.proxy", "http://old-proxy"] in calls


def test_search_projects_fetches_github_trending_and_clones(tmp_path: Path) -> None:
    requested: list[str] = []

    def fake_get(url: str) -> str:
        requested.append(url)
        return '<a href="/owner/repo">repo</a><a href="/other/tool">tool</a><a href="/sponsors/x">skip</a>'

    def fake_clone(repository: dict[str, str], download_root: Path) -> dict[str, str]:
        return {**repository, "path": str(download_root / repository["repo_key"]), "action": "cloned"}

    result = searcher.search_projects(download_root=tmp_path, http_get=fake_get, clone_func=fake_clone)
    assert result["ok"] is True
    assert result["stage"] == "search_projects"
    repos = result["content"]["repositories"]
    assert [r["repo_key"] for r in repos] == ["owner/repo", "other/tool"]
    assert requested == ["https://github.com/trending"]


def test_search_projects_returns_envelope_when_trending_fetch_fails(tmp_path: Path) -> None:
    result = searcher.search_projects(
        download_root=tmp_path,
        http_get=lambda _url: (_ for _ in ()).throw(OSError("network unavailable")),
    )
    assert result["ok"] is False
    assert result["error_code"] == "TRENDING_FETCH_FAILED"


def test_search_projects_filters_non_repo_links(tmp_path: Path) -> None:
    html = '<a href="/sponsors/x">x</a><a href="/trending/y">y</a><a href="/apps/z">z</a><a href="/real/repo">ok</a>'

    def fake_clone(repository: dict[str, str], download_root: Path) -> dict[str, str]:
        return {**repository, "path": str(download_root / repository["repo_key"]), "action": "cloned"}

    result = searcher.search_projects(
        download_root=tmp_path,
        http_get=lambda _url: html,
        clone_func=fake_clone,
    )
    assert result["ok"] is True
    assert result["content"]["repositories"][0]["repo_key"] == "real/repo"


def test_search_projects_limits_to_ten(tmp_path: Path) -> None:
    links = "".join(f'<a href="/owner/repo{i}">r{i}</a>' for i in range(15))

    def fake_clone(repository: dict[str, str], download_root: Path) -> dict[str, str]:
        return {**repository, "path": str(download_root / repository["repo_key"]), "action": "cloned"}

    result = searcher.search_projects(
        download_root=tmp_path,
        http_get=lambda _url: links,
        clone_func=fake_clone,
    )
    assert len(result["content"]["repositories"]) == 10


def test_main_returns_versioned_envelope_for_invalid_json_input(monkeypatch) -> None:
    stdout = StringIO()
    monkeypatch.setattr(searcher.sys, "stdin", StringIO("{"))
    monkeypatch.setattr(searcher.sys, "stdout", stdout)
    searcher.main()
    envelope = json.loads(stdout.getvalue())
    assert envelope["ok"] is False
    assert envelope["error_code"] == "SEARCH_INPUT_INVALID"


def test_clone_does_not_run_when_proxy_setup_fails(monkeypatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], **_kwargs: object):
        calls.append(command)
        if command[-2:] == ["http.proxy", "--get"]:
            return subprocess.CompletedProcess(command, 1, "", "")
        if command[:4] == ["git", "config", "--global", "http.proxy"]:
            return subprocess.CompletedProcess(command, 1, "", "cannot set proxy")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(searcher.subprocess, "run", fake_run)
    result = searcher.clone_repository(
        {"repo_key": "owner/repo", "url": "https://github.com/owner/repo"}, tmp_path
    )
    assert result["action"] == "failed"
    assert result["error_code"] == "GIT_PROXY_SETUP_FAILED"
    assert not any(command[:2] == ["git", "clone"] for command in calls)
    assert ["git", "config", "--global", "--unset", "http.proxy"] in calls


def test_failed_clone_cleans_partial_directory_and_retries(monkeypatch, tmp_path: Path) -> None:
    attempts = 0

    def fake_run(command: list[str], **_kwargs: object):
        nonlocal attempts
        if command[-2:] == ["http.proxy", "--get"]:
            return subprocess.CompletedProcess(command, 1, "", "")
        if command[:2] == ["git", "clone"]:
            attempts += 1
            destination = Path(command[-1])
            destination.mkdir()
            if attempts == 1:
                return subprocess.CompletedProcess(command, 1, "", "clone failed")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(searcher.subprocess, "run", fake_run)
    repository = {"repo_key": "owner/repo", "url": "https://github.com/owner/repo"}
    first = searcher.clone_repository(repository, tmp_path)
    assert first["action"] == "failed"
    second = searcher.clone_repository(repository, tmp_path)
    assert second["action"] == "cloned"
    assert attempts == 2
