import analyzer_perspective5 as perspective5


def test_score_relevance_requires_successful_previous_results() -> None:
    result = perspective5.score_relevance(
        {"perspective1": {"ok": False, "repo_key": "owner/demo"}},
        user_profile="Python and Agent learner.",
        client=lambda prompt: "should not be called",
    )

    assert result["ok"] is False
    assert result["stage"] == "perspective5"
    assert result["repo_key"] == "owner/demo"
    assert result["error_code"] == "PERSPECTIVE5_INPUT_INVALID"
    assert "relevance_score" not in result


def test_score_relevance_returns_sortable_score() -> None:
    prompts = []

    def client(prompt: str) -> str:
        prompts.append(prompt)
        return "适合学习 Agent 架构，可复用工具调用模式"

    result = perspective5.score_relevance(
        {
            "perspective1": {"ok": True, "repo_key": "owner/agent", "content": "Agent 项目"},
            "perspective2": {"ok": True, "repo_key": "owner/agent", "content": "Python CLI"},
            "perspective3": {"ok": True, "repo_key": "owner/agent", "content": "工具调用"},
            "perspective4b": {"ok": True, "repo_key": "owner/agent", "content": "状态裂隙"},
            "perspective4a": {"ok": True, "repo_key": "owner/agent", "content": "核心矛盾"},
        },
        user_profile="用户熟悉 Python，正在学习 Agent 架构，希望积累可复用模式。",
        client=client,
    )

    assert result["ok"] is True
    assert result["stage"] == "perspective5"
    assert result["repo_key"] == "owner/agent"
    assert result["relevance_score"] == 85
    assert result["content"] == "适合学习 Agent 架构，可复用工具调用模式"
    for dimension in ["技术栈熟悉度", "现有项目关联度", "学习阶段匹配度", "可直接复用项"]:
        assert dimension in prompts[0]
