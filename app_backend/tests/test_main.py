# Copyright 2024 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATAROBOT_API_TOKEN", "test-token")
os.environ.setdefault("DATAROBOT_ENDPOINT", "https://example.com")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from app import STATIC_FRONTEND_AVAILABLE, is_static_frontend_available
from app.main import app

client = TestClient(app)


@pytest.mark.skipif(
    not STATIC_FRONTEND_AVAILABLE,
    reason="Static frontend build output is not available.",
)
def test_index() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"


@pytest.mark.skipif(
    not STATIC_FRONTEND_AVAILABLE,
    reason="Static frontend build output is not available.",
)
def test_reports_spa_routes() -> None:
    for path in ("/reports", "/reports/report-123"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"


def test_customize_api_routes_are_mounted() -> None:
    paths = {
        getattr(route, "path", "")
        for route in app.routes
        if getattr(route, "path", "").startswith("/api/v1")
    }

    assert "/api/v1/config/feature-flags" in paths
    assert "/api/v1/refiner" in paths
    assert "/api/v1/reports" in paths


@pytest.mark.skipif(
    not STATIC_FRONTEND_AVAILABLE,
    reason="Static frontend build output is not available.",
)
def test_favicon_file() -> None:
    response = client.get("/datarobot_favicon.png")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")


def test_static_frontend_availability_requires_build_output(tmp_path) -> None:
    static_dir = tmp_path / "static"

    assert is_static_frontend_available(static_dir, serve_static_frontend=True) is False

    static_dir.mkdir()
    assert is_static_frontend_available(static_dir, serve_static_frontend=True) is False

    (static_dir / "index.html").write_text("<html></html>", encoding="utf-8")
    assert is_static_frontend_available(static_dir, serve_static_frontend=True) is True
    assert (
        is_static_frontend_available(static_dir, serve_static_frontend=False) is False
    )


def test_env_reports_actual_static_frontend_availability() -> None:
    response = client.get("/_dr_env.js")
    assert response.status_code == 200

    payload = response.text.removeprefix("window.ENV = ").removesuffix(";")
    assert json.loads(payload)["IS_STATIC_FRONTEND"] is STATIC_FRONTEND_AVAILABLE
