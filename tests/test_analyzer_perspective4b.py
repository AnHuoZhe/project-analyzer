import analyzer_perspective4b as perspective4b


def test_analyze_hidden_risks_uses_five_cuts() -> None:
    prompts = []

    def client(prompt: str) -> str:
        prompts.append(prompt)
        return "裂隙分析结果"

    result = perspective4b.analyze_hidden_risks(
        {
            "repo_key": "owner/demo",
            "readme_excerpt": "Agent runtime.",
            "tree": ["src/runtime.py"],
            "key_files": [{"path": "src/runtime.py", "summary": "state machine"}],
        },
        client,
    )

    assert result["ok"] is True
    assert result["stage"] == "perspective4b"
    assert result["repo_key"] == "owner/demo"
    assert result["content"] == "裂隙分析结果"
    assert len(prompts) == 1
    for cut in ["数据流", "失败模式", "状态", "分层", "运维隐患"]:
        assert cut in prompts[0]


def test_analyze_hidden_risks_returns_failure_envelope() -> None:
    def client(prompt: str) -> str:
        raise TimeoutError("model timeout")

    result = perspective4b.analyze_hidden_risks({"repo_key": "owner/demo"}, client)

    assert result["ok"] is False
    assert result["stage"] == "perspective4b"
    assert result["repo_key"] == "owner/demo"
    assert result["error_code"] == "PERSPECTIVE4B_FAILED"
    assert result["recoverable"] is True
