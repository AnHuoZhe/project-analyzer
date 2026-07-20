"""Discover and clone repositories mentioned in a Bilibili video."""

import json
import logging
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.request import urlopen, ProxyHandler, build_opener, Request


LOGGER = logging.getLogger(__name__)

GITHUB_URL_PATTERN = re.compile(r"https?://(?:www\.)?github\.com/[\w.-]+/[\w.-]+(?:\.git)?/?(?:[?#][^\s]*)?")
BVID_PATTERN = re.compile(r"\b(BV[0-9A-Za-z]+)\b")
PROXY_URL = "http://127.0.0.1:7897"
TRENDING_REPO_RE = re.compile(r'href="/([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)"')
TRENDING_SKIP_PREFIXES = ("sponsors/", "trending/", "settings/", "marketplace/", "explore/", "apps/", "features/", "topics/", "collections/", "events/", "readme/", "site/", "security/", "pricing/", "about/", "contact/", "login", "join")


def _envelope_error(stage: str, error_code: str, message: str) -> dict[str, Any]:
    LOGGER.error("%s: %s", error_code, message)
    return {"schema_version": 1, "ok": False, "stage": stage, "repo_key": None,
            "error_code": error_code, "message": message, "recoverable": True}


_PROXY_HANDLER = ProxyHandler({"https": PROXY_URL, "http": PROXY_URL})
_PROXY_OPENER = build_opener(_PROXY_HANDLER)
_PROXY_OPENER.addheaders = [("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")]


def _default_http_get(url: str) -> str:
    LOGGER.info("Fetching page: %s", url)
    req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com/"})
    with _PROXY_OPENER.open(req, timeout=30) as response:  # noqa: S310 - endpoint derives from fixed Bilibili URLs.
        return response.read().decode("utf-8", errors="replace")


def _fetch_text(http_get: Callable[[str], Any], url: str) -> str:
    response = http_get(url)
    if isinstance(response, str):
        return response
    text = getattr(response, "text", None)
    if isinstance(text, str):
        return text
    raise TypeError("HTTP getter must return text or an object with text")


def extract_latest_bvid(space_html: str) -> str | None:
    """Return the first Bilibili video identifier found on a space page."""
    match = BVID_PATTERN.search(space_html)
    if not match:
        LOGGER.warning("B站空间页未找到 BV 号")
        return None
    return match.group(1)


def extract_github_urls(description: str) -> list[str]:
    """Extract ordered, de-duplicated GitHub repository URLs from a description."""
    results: list[str] = []
    seen: set[str] = set()
    for match in GITHUB_URL_PATTERN.findall(description):
        cleaned = match.rstrip("/")
        normalized = normalize_repository_url(cleaned)
        if normalized is None or normalized["repo_key"] in seen:
            continue
        seen.add(normalized["repo_key"])
        results.append(cleaned)
    LOGGER.info("从视频简介提取到 %s 个 GitHub 链接", len(results))
    return results


def normalize_repository_url(url: str) -> dict[str, str] | None:
    """Normalize a GitHub owner/repository URL into a stable repository object."""
    candidate = url.strip()
    if candidate.startswith("github.com/"):
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    if parsed.netloc.lower().removeprefix("www.") != "github.com":
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2:
        return None
    owner, repository = parts
    if repository.endswith(".git"):
        repository = repository[:-4]
    if not owner or not repository:
        return None
    repo_key = f"{owner}/{repository}".lower()
    return {"repo_key": repo_key, "url": f"https://github.com/{repo_key}"}


def normalize_repositories(urls: list[str]) -> list[dict[str, str]]:
    """Return at most ten unique normalized repository objects."""
    repositories: list[dict[str, str]] = []
    seen: set[str] = set()
    for url in urls:
        normalized = normalize_repository_url(url)
        if normalized is None or normalized["repo_key"] in seen:
            continue
        seen.add(normalized["repo_key"])
        repositories.append(normalized)
        if len(repositories) == 10:
            break
    return repositories


def _is_valid_git_worktree(destination: Path) -> bool:
    """Check that a pre-existing destination is a usable Git worktree."""
    if not destination.is_dir():
        return False
    check = subprocess.run(
        ["git", "-C", str(destination), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
        check=False,
    )
    valid = check.returncode == 0 and check.stdout.strip() == "true"
    if not valid:
        LOGGER.warning("Existing destination is not a valid Git worktree: %s", destination)
    return valid


def clone_repository(repository: dict[str, str], download_root: Path) -> dict[str, str]:
    """Clone one repository while restoring the caller's global Git proxy setting."""
    destination = download_root / repository["repo_key"].replace("/", "-")
    if _is_valid_git_worktree(destination):
        LOGGER.info("仓库已存在，跳过克隆：%s", repository["repo_key"])
        return {**repository, "path": str(destination), "action": "skipped"}

    previous = subprocess.run(
        ["git", "config", "--global", "http.proxy", "--get"],
        capture_output=True,
        text=True,
        check=False,
    )
    previous_proxy = previous.stdout.strip() if previous.returncode == 0 else None
    try:
        setup = subprocess.run(
            ["git", "config", "--global", "http.proxy", PROXY_URL],
            capture_output=True,
            text=True,
            check=False,
        )
        if setup.returncode != 0:
            LOGGER.error("Git temporary proxy setup failed: %s", setup.stderr.strip())
            return {
                **repository,
                "path": str(destination),
                "action": "failed",
                "error_code": "GIT_PROXY_SETUP_FAILED",
            }
        clone = subprocess.run(
            ["git", "clone", repository["url"], str(destination)],
            capture_output=True,
            text=True,
            check=False,
        )
        if clone.returncode != 0:
            if destination.exists():
                LOGGER.warning("Removing partial clone directory: %s", destination)
                shutil.rmtree(destination, ignore_errors=True)
            LOGGER.error("克隆失败：%s", clone.stderr.strip())
            return {**repository, "path": str(destination), "action": "failed", "error_code": "GIT_CLONE_FAILED"}
        LOGGER.info("克隆成功：%s", repository["repo_key"])
        return {**repository, "path": str(destination), "action": "cloned"}
    finally:
        if previous_proxy:
            restore = ["git", "config", "--global", "http.proxy", previous_proxy]
        else:
            restore = ["git", "config", "--global", "--unset", "http.proxy"]
        subprocess.run(restore, capture_output=True, text=True, check=False)


def _fetch_trending_repos(http_get: Callable[[str], Any]) -> list[str]:
    """Extract up to 10 unique trending repo keys from GitHub Trending."""
    html = _fetch_text(http_get, "https://github.com/trending")
    seen: set[str] = set()
    repos: list[str] = []
    for match in TRENDING_REPO_RE.findall(html):
        if match in seen:
            continue
        if match.startswith(TRENDING_SKIP_PREFIXES):
            continue
        seen.add(match)
        repos.append(match)
        if len(repos) == 10:
            break
    LOGGER.info("从 GitHub Trending 提取到 %s 个仓库", len(repos))
    return repos


def search_projects(
    uid: str = "",
    space_url: str | None = None,
    download_root: Path | str = Path("."),
    http_get: Callable[[str], Any] | None = None,
    clone_func: Callable[[dict[str, str], Path], dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Discover up to ten trending GitHub repositories and clone them."""
    getter = http_get or _default_http_get
    clone = clone_func or clone_repository
    root = Path(download_root)

    try:
        repo_keys = _fetch_trending_repos(getter)
    except Exception as error:
        return _envelope_error("trending_fetch", "TRENDING_FETCH_FAILED", str(error))

    repositories = normalize_repositories(
        [f"https://github.com/{key}" for key in repo_keys]
    )
    results = [clone(repository, root) for repository in repositories]
    return {
        "schema_version": 1,
        "ok": True,
        "stage": "search_projects",
        "repo_key": None,
        "content": {"source": "github_trending", "repositories": results},
    }


def main() -> None:
    """Read the subprocess request from stdin and write one JSON response to stdout."""
    try:
        request = json.load(sys.stdin)
        result = search_projects(
            uid=str(request["uid"]),
            space_url=request.get("space_url"),
            download_root=request["download_root"],
        )
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        result = _envelope_error("input", "SEARCH_INPUT_INVALID", str(error))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
