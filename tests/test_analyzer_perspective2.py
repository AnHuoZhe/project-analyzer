import analyzer_perspective2 as perspective2

def test_analyze_architecture_uses_profile_tree() -> None:
    result = perspective2.analyze_architecture({"repo_key":"owner/demo","tree":["src/main.py"],"key_files":[]}, lambda prompt: "模块从 main.py 启动")
    assert result["ok"] is True
    assert result["content"] == "模块从 main.py 启动"
