from pathlib import Path


def test_pulumi_stack_can_use_prebuilt_frontend_assets() -> None:
    repo_root = Path(__file__).parents[1]
    frontend_source = (repo_root / "infra" / "infra" / "app_frontend.py").read_text()
    app_backend_source = (
        repo_root / "infra" / "infra" / "app_backend.py"
    ).read_text()

    assert "SKIP_PULUMI_FRONTEND_BUILD" in frontend_source
    assert "return None" in frontend_source
    assert "if app_frontend is None" in app_backend_source
    assert "app_frontend.stdout.apply" in app_backend_source
