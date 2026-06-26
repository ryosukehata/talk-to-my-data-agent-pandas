from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]


def test_core_dependencies_include_runtime_imports_used_by_infra() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "core" / "pyproject.toml").read_text())
    dependencies = pyproject["project"]["dependencies"]

    assert "babel>=2.16,<3" in dependencies
    assert "langid==1.1.6" in dependencies
    assert "python-docx>=1.1.0,<2.0" in dependencies
