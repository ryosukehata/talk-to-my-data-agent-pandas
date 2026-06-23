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
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATAROBOT_API_TOKEN", "test-token")
os.environ.setdefault("DATAROBOT_ENDPOINT", "https://example.com")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from app import (
    STATIC_FRONTEND_AVAILABLE,
    get_app_version,
    get_frontend_runtime_env,
    get_manifest_assets,
    get_spa_template_context,
    get_static_asset_base_url,
    is_static_frontend_available,
)
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
def test_index_uses_manifest_template_assets() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert 'src="/_dr_env.js"' in response.text
    assert 'href="/assets/' in response.text
    assert 'src="/assets/' in response.text
    assert 'src="/src/main.tsx"' not in response.text


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


def test_frontend_runtime_env_preserves_static_notebook_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BASE_PATH", raising=False)
    monkeypatch.setenv("NOTEBOOK_ID", "notebook-123")
    monkeypatch.setenv("PORT", "9090")
    monkeypatch.setenv("DATAROBOT_ENDPOINT", "https://example.com")
    monkeypatch.setenv("USE_DATAROBOT_LLM_GATEWAY", "true")

    env = get_frontend_runtime_env(static_frontend_available=True)

    assert env["APP_BASE_URL"] == "notebook-sessions/notebook-123"
    assert env["BASE_PATH"] == "notebook-sessions/notebook-123"
    assert env["API_PORT"] == "9090"
    assert env["DATAROBOT_ENDPOINT"] == "https://example.com"
    assert env["IS_STATIC_FRONTEND"] is True
    assert env["USE_DATAROBOT_LLM_GATEWAY"] == "true"


def test_static_asset_base_url_adds_notebook_api_port() -> None:
    assert (
        get_static_asset_base_url(
            app_base_url="notebook-sessions/notebook-123",
            api_port="9090",
        )
        == "/notebook-sessions/notebook-123/ports/9090/"
    )
    assert (
        get_static_asset_base_url(
            app_base_url="notebook-sessions/notebook-123/ports/9090",
            api_port="9090",
        )
        == "/notebook-sessions/notebook-123/ports/9090/"
    )
    assert get_static_asset_base_url(app_base_url="/apps/custom/", api_port="9090") == (
        "/apps/custom/"
    )
    assert get_static_asset_base_url(app_base_url="", api_port="9090") == "/"


def test_manifest_assets_include_entry_css_and_modulepreload(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "_shared.js": {
                    "file": "assets/shared-abc.js",
                    "css": ["assets/shared-def.css"],
                },
                "index.html": {
                    "file": "assets/index-abc.js",
                    "isEntry": True,
                    "imports": ["_shared.js"],
                    "css": ["assets/index-def.css"],
                },
            }
        ),
        encoding="utf-8",
    )

    assets = get_manifest_assets(
        manifest_path=manifest_path,
        entry="index.html",
        asset_base_url="/apps/custom/",
    )

    assert assets == {
        "js": ["/apps/custom/assets/index-abc.js"],
        "css": [
            "/apps/custom/assets/shared-def.css",
            "/apps/custom/assets/index-def.css",
        ],
        "modulepreload": ["/apps/custom/assets/shared-abc.js"],
    }


def test_manifest_assets_are_empty_when_manifest_is_missing(tmp_path: Path) -> None:
    assert get_manifest_assets(tmp_path / "missing.json") == {
        "js": [],
        "css": [],
        "modulepreload": [],
    }


def test_spa_template_context_uses_manifest_and_runtime_asset_base(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BASE_PATH", raising=False)
    monkeypatch.setenv("NOTEBOOK_ID", "notebook-123")
    monkeypatch.setenv("PORT", "9090")
    manifest_dir = tmp_path / ".vite"
    manifest_dir.mkdir()
    (manifest_dir / "manifest.json").write_text(
        json.dumps(
            {
                "index.html": {
                    "file": "assets/index-abc.js",
                    "isEntry": True,
                    "css": ["assets/index-def.css"],
                },
            }
        ),
        encoding="utf-8",
    )

    context = get_spa_template_context(tmp_path)

    assert (
        context["env_script_url"]
        == "/notebook-sessions/notebook-123/ports/9090/_dr_env.js"
    )
    assert (
        context["favicon_url"]
        == "/notebook-sessions/notebook-123/ports/9090/datarobot_favicon.png"
    )
    assert context["js_files"] == [
        "/notebook-sessions/notebook-123/ports/9090/assets/index-abc.js"
    ]
    assert context["css_files"] == [
        "/notebook-sessions/notebook-123/ports/9090/assets/index-def.css"
    ]


def test_health_includes_app_version() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert "version" in response.json()


def test_get_app_version_reads_deploy_version_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    version_dir = tmp_path / "app"
    version_dir.mkdir()
    (version_dir / "VERSION").write_text("  v11.5.3-1-gabcdef0\n", encoding="utf-8")

    monkeypatch.setattr("app.BASE_DIR", str(version_dir))

    assert get_app_version() == "v11.5.3-1-gabcdef0"
