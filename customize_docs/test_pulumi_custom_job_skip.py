from pathlib import Path


def test_pulumi_stack_can_skip_custom_job_resources_for_cd() -> None:
    stack_source = (Path(__file__).parents[1] / "infra" / "__main__.py").read_text()

    assert "SKIP_PULUMI_CUSTOM_JOBS" in stack_source
    assert "Skipping usage export custom job creation" in stack_source
    assert "Skipping cleanup custom job creation" in stack_source
    assert "datarobot.CustomJob(" in stack_source
