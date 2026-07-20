import analyzer_perspective1 as perspective1

def test_analyze_profile_returns_model_overview() -> None:
    calls = []
    def client(prompt: str) -> str:
        calls.append(prompt)
        return "这是一个帮助开发者分析代码库的 Agent 项目。"
    result = perspective1.analyze_profile({"repo_key": "owner/demo", "readme_excerpt": "demo"}, client)
    assert result["ok"] is True
    assert result["content"] == "这是一个帮助开发者分析代码库的 Agent 项目。"
    assert "owner/demo" in calls[0]
