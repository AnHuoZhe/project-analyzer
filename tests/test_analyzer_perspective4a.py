import analyzer_perspective4a as perspective4a


def test_analyze_dialectic_requires_previous_results() -> None:
    result = perspective4a.analyze_dialectic(
        {"perspective1": {"ok": True, "content": "overview"}},
        client=lambda prompt: "should not be called",
    )

    assert result["ok"] is False
    assert result["stage"] == "perspective4a"
    assert result["error_code"] == "PERSPECTIVE4A_INPUT_INVALID"
    assert result["recoverable"] is False


def test_analyze_dialectic_consumes_named_json_results() -> None:
    prompts = []

    def client(prompt: str) -> str:
        prompts.append(prompt)
        return "辩证法分析结果"

    result = perspective4a.analyze_dialectic(
        {
            "perspective1": {"ok": True, "repo_key": "owner/demo", "content": "它是什么"},
            "perspective2": {"ok": True, "repo_key": "owner/demo", "content": "架构骨架"},
            "perspective3": {"ok": True, "repo_key": "owner/demo", "content": "六维度"},
            "perspective4b": {"ok": True, "repo_key": "owner/demo", "content": "裂隙"},
        },
        client,
    )

    assert result["ok"] is True
    assert result["stage"] == "perspective4a"
    assert result["repo_key"] == "owner/demo"
    assert result["content"] == "辩证法分析结果"
    assert len(prompts) == 1
    assert "矛盾" in prompts[0]
    assert "它是什么" in prompts[0]
    assert "裂隙" in prompts[0]
