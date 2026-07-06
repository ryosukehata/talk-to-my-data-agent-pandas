from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = REPOSITORY_ROOT / "docker" / "Dockerfile"
START_SCRIPT = REPOSITORY_ROOT / "app_backend" / "start-app.sh"
APP_BACKEND_INFRA = REPOSITORY_ROOT / "infra" / "infra" / "app_backend.py"
PULUMI_UP_WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "pulumi-up.yml"


def test_dockerfile_uses_chainguard_fips_python_dev_image() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    assert (
        "FROM datarobot/mirror_chainguard_datarobot.com_python-fips:3.12-dev"
        in dockerfile
    )


def test_dockerfile_installs_runtime_shell_and_japanese_fonts_with_wolfi_apk() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    start_script = START_SCRIPT.read_text(encoding="utf-8")

    assert "apk add --no-cache" in dockerfile
    assert "bash" in dockerfile
    assert start_script.startswith("#!/usr/bin/env bash")
    assert "fontconfig" in dockerfile
    assert "font-noto-cjk" in dockerfile
    assert "apt-get" not in dockerfile


def test_dockerfile_runs_application_as_non_root_user() -> None:
    dockerfile_lines = DOCKERFILE.read_text(encoding="utf-8").splitlines()
    user_lines = [
        line.strip() for line in dockerfile_lines if line.strip().startswith("USER ")
    ]

    assert user_lines[0] == "USER root"
    assert user_lines[-1] == "USER 65532:65532"
    assert "chown -R 65532:65532 /opt/code" in "\n".join(dockerfile_lines)


def test_start_script_uses_writable_uv_runtime_paths_for_non_root_container() -> None:
    start_script = START_SCRIPT.read_text(encoding="utf-8")

    assert 'RUNTIME_DIR="${TMPDIR:-/tmp}/datarobot-app-runtime"' in start_script
    assert 'export UV_CACHE_DIR="${UV_CACHE_DIR:-${RUNTIME_DIR}/uv-cache}"' in (
        start_script
    )
    assert (
        'export UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-${RUNTIME_DIR}/.venv}"'
        in start_script
    )
    assert 'export UV_CACHE_DIR="${WORKING_DIR}/.uv"' not in start_script
    assert 'rm -rf "$UV_PROJECT_ENVIRONMENT"' in start_script
    assert 'cp -r "$PREBUNDLED_VENV" "$UV_PROJECT_ENVIRONMENT"' in start_script
    assert "uv sync --frozen" in start_script
    assert "uv run --frozen python -m uvicorn" in start_script


def test_pulumi_manages_app_environment_from_dockerfile_by_default() -> None:
    source = APP_BACKEND_INFRA.read_text(encoding="utf-8")

    assert "USE_JAPANESE_FONT_ENV" not in source
    assert "datarobot.ExecutionEnvironment(" in source
    assert (
        'docker_context_path=os.fspath((project_root / "docker").resolve())' in source
    )
    assert "base_environment_id = app_environment.id" in source
    assert "base_environment_version_id = app_environment.version_id" in source
    assert "RuntimeEnvironments.PYTHON_312_APPLICATION_BASE" not in source


def test_env_template_documents_pulumi_managed_dockerfile_environment() -> None:
    env_template = (REPOSITORY_ROOT / ".env.template").read_text(encoding="utf-8")

    assert "USE_JAPANESE_FONT_ENV" not in env_template
    assert "docker/Dockerfile" in env_template
    assert "APPLICATION_EXECUTION_ENVIRONMENT_ID" in env_template


def test_cd_uses_pulumi_managed_dockerfile_environment() -> None:
    workflow = PULUMI_UP_WORKFLOW.read_text(encoding="utf-8")

    assert "APPLICATION_EXECUTION_ENVIRONMENT_ID" not in workflow
    assert "APPLICATION_EXECUTION_ENVIRONMENT_VERSION_ID" not in workflow
    assert "USE_JAPANESE_FONT_ENV" not in workflow
