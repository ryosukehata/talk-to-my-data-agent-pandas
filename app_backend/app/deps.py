# Copyright 2025 DataRobot, Inc.
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

import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncGenerator

from app.config import Config

logger = logging.getLogger(__name__)


@dataclass
class Deps:
    config: Config


@asynccontextmanager
async def create_deps(
    config: Config, deps: Deps | None = None
) -> AsyncGenerator[Deps, None]:
    """Create app-scoped dependencies for startup and shutdown."""
    if deps:
        yield deps
        return

    yield Deps(config=config)
