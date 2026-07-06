import asyncio
import json
import logging
from types import SimpleNamespace
from typing import Any

import pytest

from core import dr_helper


class _FakeAsyncClient:
    response: Any = None
    requests: list[dict[str, Any]] = []
    events: list[tuple[str, Any]] = []

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def post(
        self,
        url: str,
        json: dict[str, Any],
        headers: dict[str, str],
        timeout: int,
    ) -> Any:
        self.events.append(("post", url))
        self.requests.append(
            {
                "url": url,
                "json": json,
                "headers": headers,
                "timeout": timeout,
            }
        )
        return self.response


def _setup_actuals_post(monkeypatch: pytest.MonkeyPatch, response: Any) -> None:
    _FakeAsyncClient.response = response
    _FakeAsyncClient.requests = []
    _FakeAsyncClient.events = []

    async def fake_sleep(seconds: float) -> None:
        _FakeAsyncClient.events.append(("sleep", seconds))

    monkeypatch.setattr(
        dr_helper,
        "initialize_deployment",
        lambda: (
            SimpleNamespace(headers={"Authorization": "Token test"}),
            "https://app.example/api/v2/deployments/deployment-123/",
        ),
    )
    monkeypatch.setattr(
        dr_helper, "asyncio", SimpleNamespace(sleep=fake_sleep), raising=False
    )
    monkeypatch.setattr(dr_helper.httpx, "AsyncClient", _FakeAsyncClient)


def test_actuals_post_waits_before_submitting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _setup_actuals_post(
        monkeypatch,
        SimpleNamespace(
            status_code=202,
            headers={},
            text="",
        ),
    )

    asyncio.run(
        dr_helper.async_submit_actuals_to_datarobot(
            association_id="association-123",
            telemetry_json={"query_type": "03_generate_code_file"},
        )
    )

    assert _FakeAsyncClient.events == [
        ("sleep", dr_helper._ACTUALS_POST_DELAY_SECONDS),
        (
            "post",
            "https://app.example/api/v2/deployments/deployment-123/actuals/fromJSON/",
        ),
    ]


def test_actuals_post_snapshots_telemetry_before_delay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    telemetry_json = {"query_type": "03_generate_code_file"}
    _setup_actuals_post(
        monkeypatch,
        SimpleNamespace(
            status_code=202,
            headers={},
            text="",
        ),
    )

    async def mutate_during_sleep(seconds: float) -> None:
        _FakeAsyncClient.events.append(("sleep", seconds))
        telemetry_json["query_type"] = "mutated"

    monkeypatch.setattr(
        dr_helper, "asyncio", SimpleNamespace(sleep=mutate_during_sleep)
    )

    asyncio.run(
        dr_helper.async_submit_actuals_to_datarobot(
            association_id="association-123",
            telemetry_json=telemetry_json,
        )
    )

    actual_value = json.loads(
        _FakeAsyncClient.requests[0]["json"]["data"][0]["actualValue"]
    )
    assert actual_value["query_type"] == "03_generate_code_file"


def test_actuals_post_logs_status_location_and_association_id(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _setup_actuals_post(
        monkeypatch,
        SimpleNamespace(
            status_code=202,
            headers={"Location": "/api/v2/asyncJobs/job-123/"},
            text="",
        ),
    )

    with caplog.at_level(logging.INFO, logger="DataAnalystBackend"):
        asyncio.run(
            dr_helper.async_submit_actuals_to_datarobot(
                association_id="association-123",
                telemetry_json={"query_type": "03_generate_code_file"},
            )
        )

    assert _FakeAsyncClient.requests[0]["url"] == (
        "https://app.example/api/v2/deployments/deployment-123/actuals/fromJSON/"
    )
    log_text = caplog.text
    assert "association_id=association-123" in log_text
    assert "status_code=202" in log_text
    assert "location=/api/v2/asyncJobs/job-123/" in log_text
    assert "deployment-123/actuals/fromJSON/" in log_text


def test_actuals_post_logs_non_success_response_body(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _setup_actuals_post(
        monkeypatch,
        SimpleNamespace(
            status_code=422,
            headers={},
            text='{"message":"association id was not found"}',
        ),
    )

    with caplog.at_level(logging.INFO, logger="DataAnalystBackend"):
        asyncio.run(
            dr_helper.async_submit_actuals_to_datarobot(
                association_id="missing-association",
                telemetry_json={"query_type": "03_generate_code_file"},
            )
        )

    log_text = caplog.text
    assert "Actuals post failed" in log_text
    assert "association_id=missing-association" in log_text
    assert "status_code=422" in log_text
    assert "association id was not found" in log_text
