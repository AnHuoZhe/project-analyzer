import analyzer_perspective3 as perspective3


VALID_CONTENT = {
    "context_engineering": {
        "applicable": True,
        "judgement": "good",
        "evidence": ["README describes prompt context"],
        "recommendations": ["Keep context bounded"],
    },
    "memory_system": {
        "applicable": False,
        "judgement": "not_applicable",
        "evidence": ["No memory component found"],
        "recommendations": ["Document memory decision"],
    },
    "tool_calling": {
        "applicable": True,
        "judgement": "good",
        "evidence": ["agent/core.py handles tools"],
        "recommendations": ["Add timeout tests"],
    },
    "reliability": {
        "applicable": True,
        "judgement": "bad",
        "evidence": ["No retry evidence"],
        "recommendations": ["Add retry envelope"],
    },
    "cost_control": {
        "applicable": False,
        "judgement": "not_applicable",
        "evidence": ["No model billing path"],
        "recommendations": ["State cost assumptions"],
    },
    "evaluation": {
        "applicable": True,
        "judgement": "bad",
        "evidence": ["No eval files"],
        "recommendations": ["Add smoke eval"],
    },
}


def test_non_agent_project_is_not_applicable() -> None:
    result = perspective3.analyze_engineering(
        {
            "repo_key": "owner/web-ui",
            "project_type": "frontend_library",
            "readme_excerpt": "React UI components.",
        },
        client=lambda prompt: "should not be called",
    )

    assert result["ok"] is True
    assert result["stage"] == "perspective3"
    assert result["repo_key"] == "owner/web-ui"
    assert result["content"] == "不适用"
    assert result["classification_findings"] == []


def test_agent_project_prompt_covers_six_dimensions_and_references() -> None:
    prompts = []

    def client(prompt: str) -> str:
        prompts.append(prompt)
        return {
            "content": VALID_CONTENT,
            "classification_findings": [
                {
                    "dimension": "tool_calling",
                    "label": "tool-router",
                    "finding": "Uses a central tool dispatcher",
                    "evidence": ["agent/core.py"],
                }
            ],
        }

    result = perspective3.analyze_engineering(
        {
            "repo_key": "owner/agent",
            "project_type": "agent_framework",
            "readme_excerpt": "An LLM agent framework.",
            "tree": ["agent/core.py"],
            "key_files": [{"path": "agent/core.py", "summary": "tool calling"}],
        },
        client=client,
        ruler_text="six-dimension ruler",
        classification_text="classification library",
    )

    assert result["ok"] is True
    assert result["content"]["tool_calling"]["judgement"] == "good"
    assert result["classification_findings"][0]["dimension"] == "tool_calling"
    assert len(prompts) == 1
    for dimension in ["上下文工程", "记忆系统", "工具调用", "可靠性", "成本控制", "评估"]:
        assert dimension in prompts[0]
    assert "six-dimension ruler" in prompts[0]
    assert "classification library" in prompts[0]


def test_agent_project_rejects_invalid_schema() -> None:
    result = perspective3.analyze_engineering(
        {
            "repo_key": "owner/agent",
            "project_type": "agent_framework",
            "readme_excerpt": "An LLM agent framework.",
        },
        client=lambda prompt: {
            "content": {"context_engineering": {"applicable": True, "judgement": "good"}},
            "classification_findings": [],
        },
    )

    assert result["ok"] is False
    assert result["error_code"] == "PERSPECTIVE3_SCHEMA_INVALID"
    assert result["recoverable"] is False
