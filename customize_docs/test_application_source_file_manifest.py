from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
APP_BACKEND_SOURCE = REPO_ROOT / "infra" / "infra" / "app_backend.py"


def test_app_source_manifest_collects_core_and_customize_files_once() -> None:
    source = APP_BACKEND_SOURCE.read_text()

    assert "def get_app_backend_app_files(" in source
    assert "os.walk(" in source
    assert "app_backend_application_path, followlinks=True" in source
    assert '(project_root / "utils").glob("**/*.py")' in source
    assert '(project_root / "core").glob("**/*.py")' not in source
    assert "core/src/core/locale/{application_locale}/LC_MESSAGES/base.mo" in source
    assert "return _deduplicate_files_by_destination(source_files)" in source
    assert "utils/locale" not in source


def test_app_source_manifest_follows_core_symlink_for_uv_sync() -> None:
    source = APP_BACKEND_SOURCE.read_text()

    assert "followlinks=True" in source
    assert "file_path.relative_to(app_backend_application_path).as_posix()" in source
