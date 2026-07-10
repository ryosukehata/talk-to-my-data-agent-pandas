import pytest
from core.customize.feature_flag_config import (
    FEATURE_FLAG_ENV_VARS,
    get_feature_flags,
)


def test_report_builder_feature_flag_reads_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VITE_ENABLE_REPORT_BUILDER", "true")

    flags = get_feature_flags()

    assert flags["reportBuilderEnabled"] is True


def test_runtime_feature_flag_env_vars_include_report_builder() -> None:
    assert "VITE_ENABLE_REPORT_BUILDER" in FEATURE_FLAG_ENV_VARS.values()
