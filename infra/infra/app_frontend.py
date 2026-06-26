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

import os
import time

import pulumi
import pulumi_command as command  # type: ignore[import-not-found]
from datarobot_pulumi_utils.pulumi.stack import PROJECT_NAME

from . import project_dir


def build_frontend() -> command.local.Command | None:
    if os.environ.get("SKIP_PULUMI_FRONTEND_BUILD", "false").lower() == "true":
        return None

    frontend_dir = project_dir.parent / "app_frontend"

    return command.local.Command(
        f"Data Analyst Build Frontend [{PROJECT_NAME}]",
        create=f"cd {frontend_dir} && npm install && npm run build",
        triggers=[str(time.time())],
        opts=pulumi.ResourceOptions(depends_on=[]),
    )


app_frontend = build_frontend()

__all__ = ["app_frontend"]
