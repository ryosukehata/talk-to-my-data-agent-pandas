from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
APP_BACKEND_SOURCE = REPO_ROOT / "infra" / "infra" / "app_backend.py"


def test_app_source_manifest_collects_core_and_customize_files_once() -> None:
    source = APP_BACKEND_SOURCE.read_text()

    assert "def get_app_backend_app_files(" in source
    assert '(project_root / "utils").glob("**/*.py")' in source
    assert '(project_root / "core").glob("**/*.py")' in source
    assert "core/src/core/locale/{application_locale}/LC_MESSAGES/base.mo" in source
    assert "return _deduplicate_files_by_destination(source_files)" in source
    assert "utils/locale" not in source
