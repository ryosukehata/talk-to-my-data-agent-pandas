import argparse
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Literal
from unittest.mock import patch

import pytest

from core.scripts import transfer_database


class StubResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


class StubClient:
    def __init__(self, responses: dict[str, dict[str, Any]]) -> None:
        self.responses = responses
        self.get_calls: list[str] = []

    def get(self, url: str, timeout: int = 30) -> StubResponse:
        del timeout
        self.get_calls.append(url)
        if url not in self.responses:
            raise RuntimeError(f"No mocked response for URL: {url}")
        payload = self.responses[url]
        if payload.get("raise"):
            raise RuntimeError(str(payload["raise"]))
        return StubResponse(payload)

    def __enter__(self) -> "StubClient":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> Literal[False]:
        del exc_type, exc, tb
        return False


@dataclass
class StubStorage:
    file_names: list[str]
    fetched: list[tuple[str, str]] = field(default_factory=list)
    uploaded: list[tuple[str, str]] = field(default_factory=list)

    async def files(self) -> list[str]:
        return list(self.file_names)

    async def fetch_from_storage(self, file_name: str, local_path: str) -> None:
        self.fetched.append((file_name, local_path))

    async def save_to_storage(self, file_name: str, local_path: str) -> None:
        self.uploaded.append((file_name, local_path))


def _args(
    source_app_id: str,
    target_app_id: str,
    *,
    dry_run: bool = True,
    continue_transfer_non_conflicting: bool = False,
) -> argparse.Namespace:
    return argparse.Namespace(
        source_app_id=source_app_id,
        target_app_id=target_app_id,
        log_level="INFO",
        dry_run=dry_run,
        continue_transfer_non_conflicting=continue_transfer_non_conflicting,
    )


def _build_storage_factory(
    *,
    source_app_id: str,
    source_files: list[str],
    target_app_id: str,
    target_files: list[str],
) -> tuple[StubStorage, StubStorage, Callable[[str | None, bool], StubStorage]]:
    source_storage = StubStorage(source_files)
    target_storage = StubStorage(target_files)

    def _storage_factory(user_id: str | None, global_user: bool) -> StubStorage:
        del user_id, global_user
        app_id = os.environ["APPLICATION_ID"]
        if app_id == source_app_id:
            return source_storage
        if app_id == target_app_id:
            return target_storage
        raise RuntimeError(f"Unexpected APPLICATION_ID: {app_id}")

    return source_storage, target_storage, _storage_factory


@pytest.mark.asyncio
async def test_run_non_dry_run_transfers_files_and_follows_next_page() -> None:
    source_name = "source-app"
    target_name = "target-app"
    source_app_id = "source-id"
    target_app_id = "target-id"
    client = StubClient(
        {
            f"customApplications/{source_name}/": {"raise": "not found"},
            f"customApplications/{target_name}/": {"raise": "not found"},
            "customApplications/": {
                "data": [{"id": "other-id", "name": "other-app"}],
                "next": "customApplications/?page=2",
            },
            "customApplications/?page=2": {
                "data": [
                    {"id": source_app_id, "name": source_name},
                    {"id": target_app_id, "name": target_name},
                ],
                "next": None,
            },
            f"customApplications/{source_app_id}/": {"status": "paused"},
            f"customApplications/{target_app_id}/": {"status": "stopped"},
        }
    )
    source_storage, target_storage, storage_factory = _build_storage_factory(
        source_app_id=source_app_id,
        source_files=["alpha.csv", "nested/beta.csv"],
        target_app_id=target_app_id,
        target_files=[],
    )

    with (
        patch.dict(
            os.environ,
            {
                "DATAROBOT_API_TOKEN": "token",
                "DATAROBOT_ENDPOINT": "https://example.test",
            },
            clear=True,
        ),
        patch.object(transfer_database.dr, "Client", return_value=client),
        patch.object(transfer_database.dr.KeyValue, "list", return_value=[]),
        patch.object(
            transfer_database, "PersistentStorage", side_effect=storage_factory
        ),
    ):
        rc = await transfer_database.run(_args(source_name, target_name, dry_run=False))

    assert rc == 0
    assert "customApplications/?page=2" in client.get_calls
    assert [name for name, _ in source_storage.fetched] == [
        "alpha.csv",
        "nested/beta.csv",
    ]
    assert [name for name, _ in target_storage.uploaded] == [
        "alpha.csv",
        "nested/beta.csv",
    ]


@pytest.mark.asyncio
async def test_run_dry_run_does_not_upload() -> None:
    source_app_id = "source-id"
    target_app_id = "target-id"
    client = StubClient(
        {
            f"customApplications/{source_app_id}/": {"status": "paused"},
            f"customApplications/{target_app_id}/": {"status": "stopped"},
        }
    )
    source_storage, target_storage, storage_factory = _build_storage_factory(
        source_app_id=source_app_id,
        source_files=["a.csv", "b.csv"],
        target_app_id=target_app_id,
        target_files=[],
    )

    with (
        patch.dict(
            os.environ,
            {
                "DATAROBOT_API_TOKEN": "token",
                "DATAROBOT_ENDPOINT": "https://example.test",
            },
            clear=True,
        ),
        patch.object(transfer_database.dr, "Client", return_value=client),
        patch.object(transfer_database.dr.KeyValue, "list", return_value=[]),
        patch.object(
            transfer_database, "PersistentStorage", side_effect=storage_factory
        ),
    ):
        rc = await transfer_database.run(_args(source_app_id, target_app_id))

    assert rc == 0
    assert source_storage.fetched == []
    assert target_storage.uploaded == []


@pytest.mark.asyncio
async def test_run_rejects_conflicts_unless_requested() -> None:
    source_app_id = "source-id"
    target_app_id = "target-id"
    client = StubClient(
        {
            f"customApplications/{source_app_id}/": {"status": "paused"},
            f"customApplications/{target_app_id}/": {"status": "stopped"},
        }
    )
    _, _, storage_factory = _build_storage_factory(
        source_app_id=source_app_id,
        source_files=["same.csv", "new.csv"],
        target_app_id=target_app_id,
        target_files=["same.csv"],
    )

    with (
        patch.dict(
            os.environ,
            {
                "DATAROBOT_API_TOKEN": "token",
                "DATAROBOT_ENDPOINT": "https://example.test",
            },
            clear=True,
        ),
        patch.object(transfer_database.dr, "Client", return_value=client),
        patch.object(transfer_database.dr.KeyValue, "list", return_value=[]),
        patch.object(
            transfer_database, "PersistentStorage", side_effect=storage_factory
        ),
    ):
        with pytest.raises(RuntimeError, match="Conflicts"):
            await transfer_database.run(_args(source_app_id, target_app_id))


@pytest.mark.asyncio
async def test_run_requires_stopped_or_paused_apps() -> None:
    client = StubClient(
        {
            "customApplications/source-id/": {"status": "running"},
            "customApplications/target-id/": {"status": "stopped"},
        }
    )

    with (
        patch.dict(
            os.environ,
            {
                "DATAROBOT_API_TOKEN": "token",
                "DATAROBOT_ENDPOINT": "https://example.test",
            },
            clear=True,
        ),
        patch.object(transfer_database.dr, "Client", return_value=client),
    ):
        with pytest.raises(RuntimeError, match="stopped or paused"):
            await transfer_database.run(_args("source-id", "target-id"))
