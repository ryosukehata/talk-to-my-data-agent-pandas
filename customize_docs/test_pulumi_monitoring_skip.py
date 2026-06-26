from pathlib import Path


def test_pulumi_stack_can_skip_monitoring_resources_for_cd() -> None:
    stack_source = (
        Path(__file__).parents[1] / "infra" / "infra" / "app_backend.py"
    ).read_text()

    assert 'DISALLOW_MONITORING_RESOURCES", "false"' in stack_source
    assert "Disallowing monitoring resources" in stack_source
    assert "create_monitoring_resources()" in stack_source
