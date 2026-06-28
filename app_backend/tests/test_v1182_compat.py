from pathlib import Path

from app.config import Config

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_app_config_accepts_empty_otel_sdk_disabled() -> None:
    config = Config(
        log_level="INFO",
        log_format="readable",
        otel_sdk_disabled="",
    )

    assert config.otel_sdk_disabled is False
    assert config.otel_exporter_otlp_endpoint == ""
    assert config.otel_exporter_otlp_headers == ""


def test_app_startup_configures_otel_from_config() -> None:
    source = (REPO_ROOT / "app_backend" / "app" / "__init__.py").read_text()

    assert "otel.configure(config)" in source


def test_datarobot_sdk_constraint_matches_v1182_requirement() -> None:
    for path in (
        REPO_ROOT / "core" / "pyproject.toml",
        REPO_ROOT / "app_backend" / "pyproject.toml",
        REPO_ROOT / "infra" / "pyproject.toml",
    ):
        assert "datarobot" in path.read_text()
        assert ">=3.13.0" in path.read_text()


def test_env_template_documents_otel_and_jdbc_configuration() -> None:
    template = (REPO_ROOT / ".env.template").read_text()
    cli_base = (REPO_ROOT / ".datarobot" / "cli" / "base.yml").read_text()

    assert "OTEL_EXPORTER_OTLP_ENDPOINT" in template
    assert "OTEL_SDK_DISABLED" in template
    assert "datarobot_jdbc" in template
    assert "JDBC_URI" in template
    assert "JDBC_CONNECTION_PARAMETERS" in template
    assert "datarobot_jdbc" in cli_base
    assert "jdbc_config" in cli_base
    assert "JDBC_CONNECTION_PARAMETERS" in cli_base


def test_infra_maps_jdbc_credentials_and_otel_runtime_parameters() -> None:
    app_backend_source = (REPO_ROOT / "infra" / "infra" / "app_backend.py").read_text()
    credential_source = (
        REPO_ROOT / "infra" / "infra" / "components" / "dr_credential.py"
    ).read_text()

    assert "OTEL_EXPORTER_OTLP_ENDPOINT" in app_backend_source
    assert "OTEL_EXPORTER_OTLP_HEADERS" in app_backend_source
    assert "OTEL_SDK_DISABLED" in app_backend_source
    assert "JDBCCredentials" in credential_source
    assert "JDBC_URI" in credential_source
    assert "JDBC_CONNECTION_PARAMETERS" in credential_source


def test_app_source_uses_root_health_probe_for_prebundled_bootstrap() -> None:
    app_backend_source = (REPO_ROOT / "infra" / "infra" / "app_backend.py").read_text()

    assert "health_endpoint_path=" not in app_backend_source
    assert "service_web_requests_on_root_path=True" in app_backend_source


def test_start_script_keeps_port_open_while_prebundled_env_syncs() -> None:
    start_script = (REPO_ROOT / "app_backend" / "start-app.sh").read_text()
    prebundled_block = start_script.split(
        'if [ -f "$PRE_BUNDLED_MARKER" ]; then', maxsplit=1
    )[1].split("if command -v uv", maxsplit=1)[0]

    assert "python3 -m http.server" in prebundled_block
    assert "TEMP_SERVER_PID" in prebundled_block
    assert "uv sync" in prebundled_block
