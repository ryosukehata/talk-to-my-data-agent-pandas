"""Shared pytest configuration for local repository-level test runs."""

from __future__ import annotations

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("DATAROBOT_ENDPOINT", "https://example.invalid/api/v2")
os.environ.setdefault("DATAROBOT_API_TOKEN", "test-token")
