"""Repository scanner."""
import logging
from pathlib import Path

LOGGER = logging.getLogger(__name__)

LANGUAGE_EXTENSIONS = {".py": "Python", ".js": "JavaScript", ".ts": "TypeScript", ".rs": "Rust", ".go": "Go", ".java": "Java", ".rb": "Ruby"}

def scan_project(path: Path | str, repo_key: str) -> dict:
    root = Path(path)
    try:
        if not root.is_dir():
            raise FileNotFoundError(root)
        readme_path = root / "README.md"
        raw_readme = readme_path.read_text(encoding="utf-8", errors="replace") if readme_path.exists() else ""
        readme = raw_readme[:12000]
        files = [item.relative_to(root).as_posix() for item in root.rglob("*") if item.is_file()]
    except (OSError, PermissionError) as error:
        LOGGER.error("扫描失败 %s: %s", repo_key, error)
        return {"schema_version": 1, "ok": False, "stage": "scan", "repo_key": repo_key, "error_code": "SCAN_FAILED", "message": str(error), "recoverable": True}
    languages = [language for extension, language in LANGUAGE_EXTENSIONS.items() if any(name.endswith(extension) for name in files)]
    entries = [name for name in files if Path(name).name == "main.py"]
    project_type = "agent_framework" if "agent" in (readme + " ".join(files)).lower() else "other"
    LOGGER.info("扫描项目 %s", repo_key)
    warnings = ["readme_truncated_12000"] if len(raw_readme) > 12000 else []
    return {"schema_version": 1, "ok": True, "repo_key": repo_key, "repo_path": str(root), "project_type": project_type, "languages": languages, "tags": [project_type], "readme_excerpt": readme, "tree": files[:300], "key_files": [{"path": name, "excerpt": ""} for name in files[:20]], "truncation_warnings": warnings, "frameworks": [], "entry_files": entries}
