from __future__ import annotations

import asyncio
import json
from pathlib import Path

from core.customize.domain.report.domain import (
    QuestionStatus,
    Report,
    ReportQuestion,
    ReportStatus,
)
from core.customize.infrastructure.storage.report_storage import ReportStorage


class FakePersistentStorage:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.deleted_files: list[str] = []

    async def fetch_from_storage(self, file_name: str, local_path: str) -> None:
        if file_name not in self.files:
            return
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        Path(local_path).write_bytes(self.files[file_name])

    async def save_to_storage(self, file_name: str, local_path: str) -> None:
        await asyncio.sleep(0)
        self.files[file_name] = Path(local_path).read_bytes()

    async def delete_file(self, file_name: str) -> None:
        self.deleted_files.append(file_name)
        self.files.pop(file_name, None)


def _new_report_storage(
    *,
    tmp_path: Path,
    user_id: str,
    fake_storage: FakePersistentStorage,
    run_name: str,
) -> ReportStorage:
    storage = ReportStorage(user_id)
    storage._storage = fake_storage
    storage._base_dir = tmp_path / run_name
    storage._base_dir.mkdir(parents=True, exist_ok=True)
    return storage


def _report(*, report_id: str, user_id: str) -> Report:
    return Report(
        report_id=report_id,
        title="Sales report",
        theme="売上要因を分析したい",
        user_id=user_id,
        status=ReportStatus.COMPLETED,
        questions=[
            ReportQuestion(
                question_id="question-1",
                original_direction="売上の前年差を知りたい",
                refined_question="売上の前年差を店舗別に集計して",
                status=QuestionStatus.COMPLETED,
            )
        ],
    )


async def _assert_save_persists_report_and_index_before_return(
    tmp_path: Path,
) -> None:
    user_id = "user-1"
    fake_storage = FakePersistentStorage()
    storage = _new_report_storage(
        tmp_path=tmp_path,
        user_id=user_id,
        fake_storage=fake_storage,
        run_name="run-1",
    )
    report = _report(report_id="report-1", user_id=user_id)

    await storage.save(report)

    assert "report_metadata_report-1.json" in fake_storage.files
    assert "report_index_user-1" in fake_storage.files
    assert json.loads(fake_storage.files["report_index_user-1"]) == {
        "report_ids": ["report-1"]
    }


def test_save_persists_report_and_index_before_return(tmp_path: Path) -> None:
    asyncio.run(_assert_save_persists_report_and_index_before_return(tmp_path))


async def _assert_list_by_user_recovers_reports_after_new_run(
    tmp_path: Path,
) -> None:
    user_id = "user-1"
    fake_storage = FakePersistentStorage()
    first_run_storage = _new_report_storage(
        tmp_path=tmp_path,
        user_id=user_id,
        fake_storage=fake_storage,
        run_name="run-1",
    )

    await first_run_storage.save(_report(report_id="report-1", user_id=user_id))

    second_run_storage = _new_report_storage(
        tmp_path=tmp_path,
        user_id=user_id,
        fake_storage=fake_storage,
        run_name="run-2",
    )

    reports = await second_run_storage.list_by_user(user_id)

    assert [report.report_id for report in reports] == ["report-1"]


def test_list_by_user_recovers_reports_from_storage_after_new_run(
    tmp_path: Path,
) -> None:
    asyncio.run(_assert_list_by_user_recovers_reports_after_new_run(tmp_path))
