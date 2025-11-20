import json
import os
import tempfile
from typing import Any, Callable, List, Optional

import pandas as pd

from utils.logging_helper import get_logger

logger = get_logger("PersistentCache")


def atomic_write_json(path: str, obj: Any) -> None:
    dir_name = os.path.dirname(path) or "."
    os.makedirs(dir_name, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=4)
        os.replace(tmp_path, path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


def atomic_write_csv(path: str, df: pd.DataFrame) -> None:
    dir_name = os.path.dirname(path) or "."
    os.makedirs(dir_name, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            df.to_csv(f, index=False, encoding="utf-8")
        os.replace(tmp_path, path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


class PersistentCache:
    def __init__(self, storage: Any) -> None:
        self._storage = storage

    def fetch_to_file(self, key: str, local_path: str) -> None:
        try:
            self._storage.fetch_from_storage(key, local_path)
            if os.path.exists(local_path):
                logger.info(f"Cache hit for key={key}")
            else:
                logger.info(f"Cache miss for key={key}")
        except Exception as e:
            logger.warning(f"Cache fetch failed for key={key}: {e}")

    def save_from_file(self, key: str, local_path: str) -> None:
        try:
            if os.path.exists(local_path):
                self._storage.save_to_storage(key, local_path)
                logger.info(f"Cache saved for key={key}")
        except Exception as e:
            logger.warning(f"Cache save failed for key={key}: {e}")

    def get_or_load_json(
        self,
        key: str,
        local_path: str,
        loader: Callable[[], Any],
        persist_when: Optional[Callable[[Any], bool]] = None,
    ) -> Any:
        self.fetch_to_file(key, local_path)
        if os.path.exists(local_path):
            try:
                with open(local_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load JSON cache at {local_path}: {e}")

        # Load from source
        obj = loader()
        should_persist = persist_when(obj) if persist_when else bool(obj)
        if should_persist:
            try:
                atomic_write_json(local_path, obj)
                self.save_from_file(key, local_path)
            except Exception as e:
                logger.warning(f"Failed to persist JSON for key={key}: {e}")
        return obj

    def get_or_load_csv(
        self,
        key: str,
        local_path: str,
        loader: Callable[[], pd.DataFrame],
        persist_when: Optional[Callable[[pd.DataFrame], bool]] = None,
    ) -> pd.DataFrame:
        self.fetch_to_file(key, local_path)
        if os.path.exists(local_path):
            try:
                return pd.read_csv(local_path, encoding="utf-8", dtype=str)
            except Exception as e:
                logger.warning(f"Failed to load CSV cache at {local_path}: {e}")

        # Load from source
        df = loader()
        should_persist = (
            persist_when(df)
            if persist_when is not None
            else (df is not None and not df.empty)
        )
        if should_persist:
            try:
                atomic_write_csv(local_path, df)
                self.save_from_file(key, local_path)
            except Exception as e:
                logger.warning(f"Failed to persist CSV for key={key}: {e}")
        return df


class NullPersistentStorage:
    def __init__(self, user_id: Optional[str]):
        self.user_id = user_id
        self.logger = get_logger("NullPersistentStorage")

    def files(self) -> List[str]:
        return []

    def fetch_from_storage(self, file_name: str, local_path: str) -> None:
        self.logger.debug(
            f"[Null] fetch_from_storage skipped for user_id={self.user_id}, file={file_name}"
        )

    def save_to_storage(self, file_name: str, local_path: str) -> None:
        self.logger.debug(
            f"[Null] save_to_storage skipped for user_id={self.user_id}, file={file_name}"
        )

    def delete_file(self, file_name: str) -> None:
        self.logger.debug(
            f"[Null] delete_file skipped for user_id={self.user_id}, file={file_name}"
        )
