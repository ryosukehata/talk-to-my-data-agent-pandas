from __future__ import annotations

import base64
import os
from pathlib import Path
from urllib.parse import urlencode

from pydantic import ValidationError

from core.credentials import JDBCCredentials, SnowflakeCredentials


def _explicit_jdbc_uri_configured() -> bool:
    return bool(os.getenv("JDBC_URI") or os.getenv("MLOPS_RUNTIME_PARAM_JDBC_URI"))


def _snowflake_account_host(account: str) -> str:
    host = account.strip()
    for prefix in ("jdbc:snowflake://", "https://", "http://"):
        if host.startswith(prefix):
            host = host.removeprefix(prefix)
            break
    host = host.split("?", maxsplit=1)[0].rstrip("/")
    if host.endswith(".snowflakecomputing.com"):
        return host
    return f"{host}.snowflakecomputing.com"


def _snowflake_legacy_connection_parameters(
    credentials: SnowflakeCredentials,
) -> dict[str, str]:
    parameters: dict[str, str] = {}
    if credentials.user:
        parameters["user"] = credentials.user

    if credentials.snowflake_key_path:
        if private_key_file := _read_snowflake_private_key_file(credentials):
            parameters["private_key_base64"] = base64.b64encode(
                private_key_file
            ).decode("ascii")
            if credentials.password:
                parameters["private_key_pwd"] = credentials.password
    elif credentials.password:
        parameters["password"] = credentials.password

    return parameters


def _private_key_project_roots() -> tuple[Path, ...]:
    repo_root = Path(__file__).resolve().parents[4]
    cwd = Path.cwd()
    return (cwd, cwd.parent, repo_root)


def _read_snowflake_private_key_file(
    credentials: SnowflakeCredentials,
) -> bytes | None:
    if not credentials.snowflake_key_path:
        return None

    key_path = Path(credentials.snowflake_key_path)
    for project_root in _private_key_project_roots():
        resolved_path = key_path if key_path.is_absolute() else project_root / key_path
        if resolved_path.exists():
            return resolved_path.read_bytes()
    return None


def snowflake_jdbc_credentials_from_legacy_env() -> JDBCCredentials | None:
    """Build JDBC credentials from legacy Snowflake env vars when JDBC_URI is absent."""
    if _explicit_jdbc_uri_configured():
        return None

    try:
        snowflake_credentials = SnowflakeCredentials()
    except ValidationError:
        return None

    if not snowflake_credentials.is_configured():
        return None

    query_params = {
        "warehouse": snowflake_credentials.warehouse,
        "db": snowflake_credentials.database,
        "schema": snowflake_credentials.db_schema,
        "role": snowflake_credentials.role,
    }
    jdbc_uri = (
        f"jdbc:snowflake://{_snowflake_account_host(snowflake_credentials.account)}/"
        f"?{urlencode(query_params)}"
    )
    return JDBCCredentials.model_validate(
        {
            "JDBC_URI": jdbc_uri,
            "JDBC_CONNECTION_PARAMETERS": _snowflake_legacy_connection_parameters(
                snowflake_credentials
            ),
        }
    )
