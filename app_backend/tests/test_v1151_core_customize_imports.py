import importlib
import os

import pytest


def _set_required_import_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPLICATION_ID", "test-app")
    monkeypatch.setenv("DATAROBOT_API_TOKEN", "test-token")
    monkeypatch.setenv("DATAROBOT_ENDPOINT", "https://example.com")
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")


@pytest.mark.parametrize(
    ("core_module_name", "legacy_module_name", "exported_name"),
    [
        (
            "core.customize.feature_flag_config",
            "utils.customize.feature_flag_config",
            "get_feature_flags",
        ),
        (
            "core.customize.domain.question_refiner.domain",
            "utils.customize.domain.question_refiner.domain",
            "QuestionRefinementRequest",
        ),
        (
            "core.customize.domain.report.domain",
            "utils.customize.domain.report.domain",
            "Report",
        ),
        (
            "core.customize.api_endpoints.question_refiner",
            "utils.customize.api_endpoints.question_refiner",
            "refiner_router",
        ),
        (
            "core.customize.api_endpoints.report",
            "utils.customize.api_endpoints.report",
            "report_router",
        ),
    ],
)
def test_core_customize_and_legacy_import_paths_share_exports(
    monkeypatch: pytest.MonkeyPatch,
    core_module_name: str,
    legacy_module_name: str,
    exported_name: str,
) -> None:
    _set_required_import_env(monkeypatch)

    core_module = importlib.import_module(core_module_name)
    legacy_module = importlib.import_module(legacy_module_name)

    assert getattr(legacy_module, exported_name) is getattr(core_module, exported_name)


def test_core_customize_is_the_canonical_implementation_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_required_import_env(monkeypatch)

    module = importlib.import_module("core.customize.api_endpoints.report")

    assert os.path.normpath("core/src/core/customize") in os.path.normpath(
        module.__file__ or ""
    )
