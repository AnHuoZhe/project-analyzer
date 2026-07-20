"""Project bootstrap smoke test."""


def test_searcher_module_is_importable() -> None:
    import searcher

    assert searcher is not None
