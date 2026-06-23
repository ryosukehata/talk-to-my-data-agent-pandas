# Copyright 2025 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import logging
import sys
import time
import traceback
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Literal, Union


class LogLevel(str, Enum):
    ERROR = "ERROR"
    WARN = "WARNING"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"


FormatType = Literal["json", "text", "readable"]
_READABLE_INDENT = "   "

_STANDARD_LOG_RECORD_ATTRS = set(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
)
_OTHER_LOG_RECORD_ATTRS = set({"asctime", "message", "color_message"})
_ALL_EXCLUDED_LOG_RECORD_ATTRS = _STANDARD_LOG_RECORD_ATTRS.union(
    _OTHER_LOG_RECORD_ATTRS
)


class JsonFormatter(logging.Formatter):
    """JSON formatter that includes explicitly provided extra fields."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.default_fields: Dict[
            str, Union[Callable[[logging.LogRecord], Any], Any]
        ] = {
            "timestamp": lambda _: datetime.now(timezone.utc).isoformat(),
            "level": lambda record: record.levelname,
            "logger": lambda record: record.name,
        }

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            field: getter(record) if callable(getter) else getter
            for field, getter in self.default_fields.items()
        }
        log_data["message"] = record.getMessage()

        if record.exc_info and record.exc_info[0]:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": "".join(traceback.format_exception(*record.exc_info)),
            }

        extra_fields = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _ALL_EXCLUDED_LOG_RECORD_ATTRS
        }
        for key, value in extra_fields.items():
            try:
                json.dumps(value, default=str)
                log_data[key] = value
            except ValueError as e:
                log_data[key] = f"<serialization error: {str(e)}>"

        return json.dumps(log_data, ensure_ascii=False, default=str)


class ReadableFormatter(logging.Formatter):
    """Compact human-readable formatter that still preserves extra fields."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()
        message = f"{timestamp} {record.levelname}:{record.name}:{record.getMessage()}"
        extra_fields = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _ALL_EXCLUDED_LOG_RECORD_ATTRS
        }
        if extra_fields:
            extra_str = " | ".join(
                f"{key}={value}" for key, value in extra_fields.items()
            )
            message = f"{message} | {extra_str}"

        if not (record.exc_info and record.exc_info[0]):
            return message

        tb_str = "".join(traceback.format_exception(*record.exc_info))
        tb_indented = "\n".join(
            f"{_READABLE_INDENT}{line}" for line in tb_str.rstrip().split("\n")
        )
        return f"{message}\n{_READABLE_INDENT}exception:\n{tb_indented}"


class TextFormatter(logging.Formatter):
    """Text formatter that appends explicitly provided extra fields."""

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        extra_fields = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _ALL_EXCLUDED_LOG_RECORD_ATTRS
        }
        if extra_fields:
            extra_str = " | ".join(
                f"{key}={value}" for key, value in extra_fields.items()
            )
            message = f"{message} | {extra_str}"
        return message


def init_logging(
    level: LogLevel = LogLevel.INFO,
    format_type: FormatType = "text",
    stream: Any | None = None,
) -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(level.value)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout if stream is None else stream)
    if format_type == "json":
        handler.setFormatter(JsonFormatter())
    elif format_type == "readable":
        handler.setFormatter(ReadableFormatter())
    else:
        text_formatter = TextFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        text_formatter.converter = time.gmtime
        handler.setFormatter(text_formatter)

    root_logger.addHandler(handler)
