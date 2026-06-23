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
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Awaitable, Callable

from core.rest_api import create_app as create_core_app
from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import Config
from app.deps import Deps, create_deps
from app.telemetry import configure_uvicorn_logging, init_logging

try:
    from datarobot_asgi_middleware import DataRobotASGIMiddleware
except ImportError:
    DataRobotASGIMiddleware = None  # type: ignore[assignment, misc]

# Configure logging to filter out the health check logs
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Filter out "GET /" health check logs
        return "GET / HTTP/1.1" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(EndpointFilter())

SCRIPT_NAME = os.environ.get("SCRIPT_NAME", "")
SERVE_STATIC_FRONTEND = os.getenv("SERVE_STATIC_FRONTEND", "True").casefold() == "true"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
base_router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)
_configured_app: FastAPI | None = None


def get_app_version() -> str:
    version_file = os.path.join(BASE_DIR, "VERSION")
    if os.path.isfile(version_file):
        with open(version_file, encoding="utf-8") as file:
            return file.read().strip()
    return ""


@base_router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "version": get_app_version()}


def is_static_frontend_available(
    static_dir: str | os.PathLike[str],
    serve_static_frontend: bool,
) -> bool:
    if not serve_static_frontend:
        return False

    return os.path.isdir(static_dir) and os.path.isfile(
        os.path.join(static_dir, "index.html")
    )


def get_app_base_url() -> str:
    notebook_id = os.getenv("NOTEBOOK_ID", "")
    app_base_url = os.getenv("BASE_PATH", "")
    if not app_base_url and notebook_id:
        app_base_url = f"notebook-sessions/{notebook_id}"

    return app_base_url


def get_frontend_runtime_env(static_frontend_available: bool) -> dict[str, object]:
    app_base_url = get_app_base_url()

    return {
        "APP_BASE_URL": app_base_url,
        "BASE_PATH": app_base_url,
        "API_PORT": os.getenv("PORT"),
        "DATAROBOT_ENDPOINT": os.getenv("DATAROBOT_ENDPOINT", ""),
        "APP_VERSION": get_app_version(),
        "IS_STATIC_FRONTEND": static_frontend_available,
        "USE_DATAROBOT_LLM_GATEWAY": os.getenv("USE_DATAROBOT_LLM_GATEWAY", "false"),
    }


def get_static_asset_base_url(app_base_url: str, api_port: str | None) -> str:
    normalized_base = app_base_url.strip("/")
    if not normalized_base:
        return "/"

    if (
        "notebook-sessions" in normalized_base
        and "/ports/" not in f"/{normalized_base}/"
        and api_port
    ):
        normalized_base = f"{normalized_base}/ports/{api_port}"

    return f"/{normalized_base}/"


def _empty_manifest_assets() -> dict[str, list[str]]:
    return {"js": [], "css": [], "modulepreload": []}


def _append_unique(items: list[str], item: str) -> None:
    if item not in items:
        items.append(item)


def _format_asset_url(asset_path: str, asset_base_url: str) -> str:
    normalized_base = asset_base_url or "/"
    if not normalized_base.endswith("/"):
        normalized_base = f"{normalized_base}/"

    return f"{normalized_base}{asset_path.lstrip('/')}"


def get_manifest_assets(
    manifest_path: str | os.PathLike[str],
    entry: str = "index.html",
    asset_base_url: str = "/",
) -> dict[str, list[str]]:
    manifest_file = Path(manifest_path)
    if not manifest_file.is_file():
        return _empty_manifest_assets()

    with manifest_file.open(encoding="utf-8") as file:
        manifest = json.load(file)

    entry_data = manifest.get(entry)
    if not isinstance(entry_data, dict):
        return _empty_manifest_assets()

    assets = _empty_manifest_assets()
    visited_imports: set[str] = set()

    def collect_import(import_name: str) -> None:
        if import_name in visited_imports:
            return
        visited_imports.add(import_name)

        import_data = manifest.get(import_name)
        if not isinstance(import_data, dict):
            return

        for nested_import in import_data.get("imports", []):
            if isinstance(nested_import, str):
                collect_import(nested_import)

        import_file = import_data.get("file")
        if isinstance(import_file, str):
            _append_unique(
                assets["modulepreload"],
                _format_asset_url(import_file, asset_base_url),
            )

        for css_file in import_data.get("css", []):
            if isinstance(css_file, str):
                _append_unique(
                    assets["css"],
                    _format_asset_url(css_file, asset_base_url),
                )

    for import_name in entry_data.get("imports", []):
        if isinstance(import_name, str):
            collect_import(import_name)

    for css_file in entry_data.get("css", []):
        if isinstance(css_file, str):
            _append_unique(assets["css"], _format_asset_url(css_file, asset_base_url))

    entry_file = entry_data.get("file")
    if isinstance(entry_file, str):
        assets["js"].append(_format_asset_url(entry_file, asset_base_url))

    return assets


def get_spa_template_context(static_dir: str | os.PathLike[str]) -> dict[str, object]:
    env_vars = get_frontend_runtime_env(STATIC_FRONTEND_AVAILABLE)
    asset_base_url = get_static_asset_base_url(
        app_base_url=str(env_vars["APP_BASE_URL"]),
        api_port=(
            str(env_vars["API_PORT"]) if env_vars["API_PORT"] is not None else None
        ),
    )
    manifest_assets = get_manifest_assets(
        Path(static_dir) / ".vite" / "manifest.json",
        asset_base_url=asset_base_url,
    )

    return {
        "env_script_url": f"{asset_base_url}_dr_env.js",
        "favicon_url": f"{asset_base_url}datarobot_favicon.png",
        "js_files": manifest_assets["js"],
        "css_files": manifest_assets["css"],
        "modulepreload_files": manifest_assets["modulepreload"],
    }


def create_spa_response(request: Request) -> Response:
    static_dir = Path(STATIC_DIR)
    template_path = Path(TEMPLATES_DIR) / "index.html"
    manifest_path = static_dir / ".vite" / "manifest.json"
    context = get_spa_template_context(static_dir)

    if template_path.is_file() and manifest_path.is_file() and context["js_files"]:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context=context,
        )

    return FileResponse(static_dir / "index.html", media_type="text/html")


STATIC_FRONTEND_AVAILABLE = is_static_frontend_available(
    STATIC_DIR,
    SERVE_STATIC_FRONTEND,
)

if SERVE_STATIC_FRONTEND and not STATIC_FRONTEND_AVAILABLE:
    logging.getLogger(__name__).warning(
        "Static frontend build output not found at %s; skipping static frontend mount.",
        STATIC_DIR,
    )


@base_router.get("/_dr_env.js")
async def get_env() -> Response:
    env_vars = get_frontend_runtime_env(STATIC_FRONTEND_AVAILABLE)
    js = f"window.ENV = {json.dumps(env_vars)};"
    return Response(content=js, media_type="application/javascript")


# Serve runtime env script from nested paths as well to support deep reloads
@base_router.get("/{tail:path}/_dr_env.js")
async def get_env_catch_all(tail: str) -> Response:
    return await get_env()


# Serve SPA index.html for known app routes (deep reload support)
if STATIC_FRONTEND_AVAILABLE:

    @base_router.get(f"{SCRIPT_NAME}/")
    @base_router.get(f"{SCRIPT_NAME}/data")
    @base_router.get(f"{SCRIPT_NAME}/data/{{dataId:path}}")
    @base_router.get(f"{SCRIPT_NAME}/chats")
    @base_router.get(f"{SCRIPT_NAME}/chats/{{chat_id:path}}")
    @base_router.get(f"{SCRIPT_NAME}/reports")
    @base_router.get(f"{SCRIPT_NAME}/reports/{{report_id:path}}")
    async def serve_spa(request: Request) -> Response:
        return create_spa_response(request)


def create_static_path_middleware() -> Callable[
    [Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]
]:
    async def static_path_normalize(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        path = request.scope.get("path")
        if isinstance(path, str):
            # If already canonical, leave it. If nested, collapse to canonical tail.
            if path.startswith("/assets/"):
                return await call_next(request)
            if "/assets/" in path:
                assets_idx = path.find("/assets/")
                request.scope["path"] = path[assets_idx:]
        return await call_next(request)

    return static_path_normalize


def _add_datarobot_asgi_middleware(app: FastAPI) -> None:
    if DataRobotASGIMiddleware is None:
        logging.getLogger(__name__).warning(
            "datarobot-asgi-middleware is not installed; skipping DataRobot ASGI middleware."
        )
        return

    app.add_middleware(DataRobotASGIMiddleware, health_endpoint="/health")


def create_app(
    title: str = "Data Analyst API",
    config: Config | None = None,
    deps: Deps | None = None,
) -> FastAPI:
    global _configured_app

    cacheable = title == "Data Analyst API" and config is None and deps is None
    if cacheable and _configured_app is not None:
        return _configured_app

    if config is None:
        config = Config()

    init_logging(level=config.log_level, format_type=config.log_format)
    configure_uvicorn_logging(
        log_format=config.log_format,
        log_level=config.log_level.value,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        async with create_deps(config, deps) as dependencies:
            app.state.deps = dependencies
            yield

    app = create_core_app(lifespan=lifespan, title=title)
    _add_datarobot_asgi_middleware(app)
    app.include_router(base_router)

    if STATIC_FRONTEND_AVAILABLE:
        app.middleware("http")(create_static_path_middleware())

        # Important to be last so that we fall back to the static files if the route is not found
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

    if cacheable:
        _configured_app = app
    return app
