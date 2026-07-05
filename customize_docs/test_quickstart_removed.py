from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]


def test_legacy_quickstart_script_is_removed() -> None:
    assert not (REPO_ROOT / "quickstart.py").exists()


def test_readme_uses_taskfile_for_pulumi_setup() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "quickstart.py" not in readme
    assert "pip install -r requirements.txt" not in readme
    assert "pulumi down" not in readme
    assert "task infra:select -- YOUR_PROJECT_NAME --create" in readme
    assert "task infra:down-yes" in readme
    assert "task deploy" in readme
    assert "uv run pulumi up" in readme


def test_windows_env_loader_has_no_quickstart_dependency() -> None:
    set_env_bat = (REPO_ROOT / "set_env.bat").read_text(encoding="utf-8")
    set_env_ps1 = (REPO_ROOT / "Set-Env.ps1").read_text(encoding="utf-8")

    assert "quickstart" not in set_env_bat
    assert "quickstart" not in set_env_ps1
    assert "set_env_vars.bat" in set_env_bat


def test_agent_guidelines_use_taskfile_pulumi_entrypoint() -> None:
    agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert "quickstart.py" not in agents
    assert "dr start" in agents
    assert "task deploy" in agents
