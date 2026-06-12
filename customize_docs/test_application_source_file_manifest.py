from __future__ import annotations

import sys
from collections import Counter
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace

import pulumi_datarobot as datarobot


def test_app_source_file_destinations_are_unique(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENVIRONMENT_ID", "test-env")
    monkeypatch.setenv("PULUMI_STACK_CONTEXT", "test-stack")
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "infra"))
    monkeypatch.setattr(
        datarobot.ExecutionEnvironment,
        "get",
        staticmethod(
            lambda id, resource_name: SimpleNamespace(id=id)  # noqa: A002
        ),
    )
    sys.modules.pop("infra.settings_app_infra", None)

    settings_app_infra = import_module("infra.settings_app_infra")
    monkeypatch.setattr(
        settings_app_infra,
        "_prep_metadata_yaml",
        lambda runtime_parameter_values: None,
    )

    destination_counts = Counter(
        destination for _, destination in settings_app_infra.get_app_files([])
    )
    duplicate_destinations = sorted(
        destination for destination, count in destination_counts.items() if count > 1
    )

    assert duplicate_destinations == []
    assert destination_counts["core/src/core/rest_api.py"] == 1
    assert destination_counts["core/src/core/customize/api_endpoints/report.py"] == 1
    assert destination_counts["utils/rest_api.py"] == 1
    assert destination_counts["utils/customize/api_endpoints/report.py"] == 1
