import asyncio
import contextvars
import logging
from typing import Any

from core.base_telemetry import BaseTelemetry
from opentelemetry import context as otel_context


class _ContextAttachingSpan:
    def __enter__(self) -> "_ContextAttachingSpan":
        self._token = otel_context.attach(otel_context.set_value("test-span", object()))
        return self

    def __exit__(self, *_args: Any) -> None:
        otel_context.detach(self._token)

    def end(self) -> None:
        pass

    def is_recording(self) -> bool:
        return False

    def record_exception(self, _exception: BaseException) -> None:
        pass

    def set_status(self, _status: Any) -> None:
        pass


class _ContextAttachingTracer:
    def start_as_current_span(self, _name: str) -> _ContextAttachingSpan:
        return _ContextAttachingSpan()

    def start_span(self, _name: str) -> _ContextAttachingSpan:
        return _ContextAttachingSpan()


async def _run_in_context(context: contextvars.Context, awaitable: Any) -> Any:
    task = context.run(asyncio.create_task, awaitable)
    return await task


def test_trace_async_generator_close_does_not_detach_in_different_context(
    monkeypatch,
    caplog,
) -> None:
    telemetry = BaseTelemetry()
    monkeypatch.setattr(
        telemetry,
        "get_tracer",
        lambda _name: _ContextAttachingTracer(),
    )

    @telemetry.trace
    async def stream_values():
        yield "first"
        yield "second"

    async def run() -> None:
        stream = stream_values()
        assert await _run_in_context(contextvars.Context(), stream.__anext__()) == (
            "first"
        )

        with caplog.at_level(logging.ERROR, logger="opentelemetry.context"):
            await _run_in_context(contextvars.Context(), stream.aclose())

    asyncio.run(run())

    assert "Failed to detach context" not in caplog.text
