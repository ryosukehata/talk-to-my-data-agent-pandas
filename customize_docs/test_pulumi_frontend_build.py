from pathlib import Path


def test_pulumi_stack_can_use_prebuilt_frontend_assets() -> None:
    repo_root = Path(__file__).parents[1]
    frontend_source = (repo_root / "infra" / "app_frontend.py").read_text()
    stack_source = (repo_root / "infra" / "__main__.py").read_text()

    assert "SKIP_PULUMI_FRONTEND_BUILD" in frontend_source
    assert "return None" in frontend_source
    assert "if app_frontend is None" in stack_source
    assert "app_frontend.stdout.apply" in stack_source
