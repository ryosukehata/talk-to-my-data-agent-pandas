from contextlib import asynccontextmanager
from typing import AsyncGenerator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _set_required_import_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATAROBOT_API_TOKEN", "test-token")
    monkeypatch.setenv("DATAROBOT_ENDPOINT", "https://example.com")
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")


def test_backend_app_exposes_health_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_required_import_env(monkeypatch)

    from app import create_app

    response = TestClient(create_app()).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_backend_app_lifespan_initializes_deps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_required_import_env(monkeypatch)

    from app import create_app
    from app.config import Config
    from app.deps import Deps

    deps = Deps(config=Config(log_format="text"))

    with TestClient(create_app(deps=deps)) as client:
        assert client.app.state.deps is deps


def test_core_app_factory_accepts_lifespan_without_reusing_singleton(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_required_import_env(monkeypatch)

    from core import rest_api

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        app.state.integration_marker = "ready"
        yield

    created_app = rest_api.create_app(lifespan=lifespan, title="Injected API")

    assert created_app is not rest_api.app
    assert created_app.title == "Injected API"
    with TestClient(created_app) as client:
        assert client.app.state.integration_marker == "ready"


def test_session_helpers_are_extracted_and_reexported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_required_import_env(monkeypatch)

    from core import middleware, rest_api

    assert rest_api.SessionState is middleware.SessionState
    assert rest_api.session_store is middleware.session_store
    assert rest_api._initialize_session is middleware._initialize_session
