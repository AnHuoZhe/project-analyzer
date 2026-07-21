import orchestrator
from pathlib import Path


def test_run_skips_repository_when_history_matches() -> None:
    calls = {"scan": 0, "update": 0}

    result = orchestrator.run_pipeline(
        search_projects=lambda: {
            "ok": True,
            "projects": [{"repo_key": "owner/demo", "url": "https://github.com/owner/demo", "local_path": "repos/demo"}],
        },
        query_index=lambda repo_key, profile=None: {
            "ok": True,
            "found": True,
            "entry": {"repo_key": repo_key, "report_path": "reports/demo.md"},
        },
        scan_project=lambda project: calls.__setitem__("scan", calls["scan"] + 1),
        run_parallel=lambda profile: {},
        run_dialectic=lambda results: {},
        run_relevance=lambda results: {},
        update_index=lambda request: calls.__setitem__("update", calls["update"] + 1),
    )

    assert result["ok"] is True
    assert result["states"]["owner/demo"]["status"] == "skipped_analyzed"
    assert result["states"]["owner/demo"]["skip_reason"] == "history_match_before_scan"
    assert calls == {"scan": 0, "update": 0}


def test_run_analyzes_unseen_repository_and_sorts_by_relevance() -> None:
    result = orchestrator.run_pipeline(
        search_projects=lambda: {
            "ok": True,
            "projects": [{"repo_key": "owner/agent", "url": "https://github.com/owner/agent", "local_path": "repos/agent"}],
        },
        query_index=lambda repo_key, profile=None: {"ok": True, "found": False, "entry": None},
        scan_project=lambda project: {
            "ok": True,
            "repo_key": project["repo_key"],
            "repo_path": project["local_path"],
            "project_type": "agent_framework",
            "tags": ["agent", "python"],
        },
        run_parallel=lambda profile: {
            "perspective1": {"ok": True, "repo_key": profile["repo_key"], "content": "overview"},
            "perspective2": {"ok": True, "repo_key": profile["repo_key"], "content": "architecture"},
            "perspective3": {"ok": True, "repo_key": profile["repo_key"], "content": "engineering"},
            "perspective4b": {"ok": True, "repo_key": profile["repo_key"], "content": "gaps"},
        },
        run_dialectic=lambda results: {"ok": True, "repo_key": "owner/agent", "content": "dialectic"},
        run_relevance=lambda results: {
            "ok": True,
            "repo_key": "owner/agent",
            "content": "fitness",
            "relevance_score": 85,
        },
        update_index=lambda request: {"ok": True, "repo_key": request["repo_key"]},
    )

    assert result["ok"] is True
    assert result["states"]["owner/agent"]["status"] == "indexed"
    assert result["states"]["owner/agent"]["transitions"] == [
        "history_checked",
        "scanned",
        "parallel_analyzed",
        "dialectic_analyzed",
        "fitness_analyzed",
        "indexed",
    ]
    assert result["results"][0]["repo_key"] == "owner/agent"
    assert result["results"][0]["relevance_score"] == 85


def test_run_json_subprocess_round_trips_stdin_stdout(tmp_path: Path) -> None:
    script = tmp_path / "worker.py"
    script.write_text(
        "import json, sys\n"
        "payload = json.load(sys.stdin)\n"
        "json.dump({'ok': True, 'echo': payload['value']}, sys.stdout)\n",
        encoding="utf-8",
    )

    result = orchestrator.run_json_subprocess(["python", str(script)], {"value": "hello"})

    assert result == {"ok": True, "echo": "hello"}


def test_run_json_subprocess_returns_failure_envelope_for_invalid_json(tmp_path: Path) -> None:
    script = tmp_path / "worker.py"
    script.write_text("print('not json')\n", encoding="utf-8")

    result = orchestrator.run_json_subprocess(["python", str(script)], {"value": "hello"})

    assert result["ok"] is False
    assert result["stage"] == "subprocess"
    assert result["error_code"] == "SUBPROCESS_JSON_INVALID"
    assert result["recoverable"] is True


def test_cli_prints_overview_and_writes_report_on_enter(tmp_path: Path) -> None:
    outputs = []
    inputs = iter([""])

    result = orchestrator.run_cli(
        pipeline=lambda: {
            "ok": True,
            "results": [
                {
                    "repo_key": "owner/agent",
                    "relevance_score": 85,
                    "analysis": {
                        "perspective1": {"content": "这是概览"},
                        "perspective2": {"content": "架构骨架"},
                        "perspective3": {"content": {"tool_calling": {"judgement": "good"}}},
                        "perspective4b": {"content": "裂隙分析"},
                        "perspective4a": {"content": "辩证分析"},
                        "perspective5": {"content": "适用性分析", "relevance_score": 85},
                    },
                }
            ],
        },
        input_func=lambda prompt="": next(inputs),
        print_func=outputs.append,
        report_dir=tmp_path,
    )

    report_files = list(tmp_path.glob("*-owner-agent-分析报告-*.docx"))
    assert len(report_files) == 1
    report_path = report_files[0]
    assert result["ok"] is True
    assert report_path.exists()
    assert report_path.stat().st_size > 0
    assert any("owner/agent" in item and "85" in item for item in outputs)


def test_cli_next_skips_report_and_q_exits(tmp_path: Path) -> None:
    outputs = []
    inputs = iter(["n", "q"])

    result = orchestrator.run_cli(
        pipeline=lambda: {
            "ok": True,
            "results": [
                {"repo_key": "owner/one", "relevance_score": 90, "analysis": {"perspective1": {"content": "one"}}},
                {"repo_key": "owner/two", "relevance_score": 80, "analysis": {"perspective1": {"content": "two"}}},
            ],
        },
        input_func=lambda prompt="": next(inputs),
        print_func=outputs.append,
        report_dir=tmp_path,
    )

    assert result["ok"] is True
    assert not list(tmp_path.glob("*-owner-one-分析报告-*.docx"))
    assert not list(tmp_path.glob("*-owner-two-分析报告-*.docx"))
    assert any("owner/one" in item for item in outputs)
    assert any("owner/two" in item for item in outputs)


def test_main_calls_cli_with_default_report_dir(monkeypatch, tmp_path: Path) -> None:
    captured = {}
    monkeypatch.setattr(orchestrator, "DEFAULT_ENV_PATH", tmp_path / ".env")
    monkeypatch.setattr(orchestrator, "DEFAULT_REPORT_DIR", tmp_path / "reports")
    orchestrator.DEFAULT_ENV_PATH.write_text("DEEPSEEK_API_KEY=test-key\n", encoding="utf-8")
    monkeypatch.setattr(orchestrator, "build_deepseek_client", lambda env: lambda prompt: "model")

    def fake_run_cli(pipeline, input_func=input, print_func=print, report_dir=None, batch_num=None):
        captured["report_dir"] = report_dir
        return {"ok": True, "stage": "cli"}

    monkeypatch.setattr(orchestrator, "run_cli", fake_run_cli)

    result = orchestrator.main()

    assert result["ok"] is True
    assert captured["report_dir"] == tmp_path / "reports"


def test_main_pipeline_uses_real_module_callbacks(monkeypatch, tmp_path: Path) -> None:
    captured = {}
    monkeypatch.setattr(orchestrator, "DEFAULT_ENV_PATH", tmp_path / ".env")
    monkeypatch.setattr(orchestrator, "DEFAULT_INDEX_PATH", tmp_path / "index.md")
    monkeypatch.setattr(orchestrator, "DEFAULT_DOWNLOAD_ROOT", tmp_path / "repos")
    monkeypatch.setattr(orchestrator, "DEFAULT_REPORT_DIR", tmp_path / "reports")
    orchestrator.DEFAULT_ENV_PATH.write_text("DEEPSEEK_API_KEY=test-key\n", encoding="utf-8")
    monkeypatch.setattr(orchestrator, "build_deepseek_client", lambda env: lambda prompt: "model")
    monkeypatch.setattr(orchestrator, "_load_text_if_exists", lambda path: "reference")
    monkeypatch.setattr(orchestrator, "_query_index", lambda path, repo_key: {"ok": True, "found": False})
    monkeypatch.setattr(orchestrator, "_update_index", lambda path, entry: {"ok": True})
    monkeypatch.setattr(orchestrator, "_search_projects", lambda **kwargs: {"ok": True, "content": {"repositories": [{"repo_key": "owner/agent", "path": str(tmp_path / "repo")} ]}})
    monkeypatch.setattr(orchestrator, "_scan_project", lambda path, repo_key: {"ok": True, "repo_key": repo_key, "repo_path": path, "project_type": "agent_framework", "tags": ["agent"]})
    monkeypatch.setattr(orchestrator, "_analyze_profile", lambda profile, client: {"ok": True, "repo_key": profile["repo_key"], "content": "overview"})
    monkeypatch.setattr(orchestrator, "_analyze_architecture", lambda profile, client: {"ok": True, "repo_key": profile["repo_key"], "content": "architecture"})
    monkeypatch.setattr(orchestrator, "_analyze_engineering", lambda profile, client, ruler_text="", classification_text="": {"ok": True, "repo_key": profile["repo_key"], "content": "engineering"})
    monkeypatch.setattr(orchestrator, "_analyze_hidden_risks", lambda profile, client: {"ok": True, "repo_key": profile["repo_key"], "content": "gaps"})
    monkeypatch.setattr(orchestrator, "_analyze_dialectic", lambda results, client: {"ok": True, "repo_key": "owner/agent", "content": "dialectic"})
    monkeypatch.setattr(orchestrator, "_score_relevance", lambda results, user_profile, client: {"ok": True, "repo_key": "owner/agent", "content": "fit", "relevance_score": 80})

    def fake_run_cli(pipeline, input_func=input, print_func=print, report_dir=None, batch_num=None):
        captured["pipeline_result"] = pipeline()
        return {"ok": True, "stage": "cli"}

    monkeypatch.setattr(orchestrator, "run_cli", fake_run_cli)

    result = orchestrator.main()

    assert result["ok"] is True
    assert captured["pipeline_result"]["ok"] is True
    assert captured["pipeline_result"]["results"][0]["repo_key"] == "owner/agent"
