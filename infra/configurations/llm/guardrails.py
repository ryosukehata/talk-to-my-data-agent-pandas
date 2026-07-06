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
"""Fork-specific LLM moderation guardrails."""

import pulumi_datarobot as datarobot
from datarobot_pulumi_utils.schema.guardrails import (
    Condition,
    GuardConditionComparator,
    ModerationAction,
    Stage,
)

prompt_tokens = datarobot.CustomModelGuardConfigurationArgs(
    name="Prompt Tokens",
    template_name="Prompt Tokens",
    stages=[Stage.PROMPT],
    intervention=datarobot.CustomModelGuardConfigurationInterventionArgs(
        action=ModerationAction.REPORT,
        condition=Condition(
            comparand="8192",
            comparator=GuardConditionComparator.GREATER_THAN,
        ).model_dump_json(),
    ),
)

response_tokens = datarobot.CustomModelGuardConfigurationArgs(
    name="Response Tokens",
    template_name="Response Tokens",
    stages=[Stage.RESPONSE],
    intervention=datarobot.CustomModelGuardConfigurationInterventionArgs(
        action=ModerationAction.REPORT,
        condition=Condition(
            comparand="8192",
            comparator=GuardConditionComparator.GREATER_THAN,
        ).model_dump_json(),
    ),
)

llm_guard_configurations = [prompt_tokens, response_tokens]
