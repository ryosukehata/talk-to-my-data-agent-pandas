# Copyright 2025 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import sys
from pathlib import Path
from typing import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (APP_BACKEND_ROOT, REPO_ROOT):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

# Set env vars before importing app (app → core loads core.config.Config at import time)
os.environ.setdefault("DATAROBOT_ENDPOINT", "https://dummy-endpoint.datarobot.com")
os.environ.setdefault("DATAROBOT_API_TOKEN", "dummy-api-token-for-tests")

from app import create_app  # noqa: E402
from app.config import Config  # noqa: E402
from app.deps import Deps  # noqa: E402


@pytest.fixture()
def config() -> Config:
    return Config()


@pytest.fixture
def deps(config: Config) -> Deps:
    """
    Dependency function to provide the necessary dependencies for the FastAPI app.
    Most of the dependencies are mocked to avoid unnecessary complexity in some tests.
    """
    return Deps(config=config)


@pytest.fixture
def webapp(config: Config, deps: Deps) -> FastAPI:
    """
    Create a FastAPI app instance with the provided configuration.
    """
    app = create_app(config=config, deps=deps)
    return app


@pytest.fixture
def client(webapp: FastAPI) -> Generator[TestClient, None, None]:
    """
    Create a test client for the FastAPI app.

    Note: This client is not authenticated by default. For authenticated endpoints,
    use the `authenticated_client` fixture instead.
    """
    with TestClient(webapp) as client:
        yield client
