"""Compatibility package entry point for the src-layout core package."""

from pathlib import Path

_src_core = Path(__file__).resolve().parent / "src" / "core"
if _src_core.is_dir():
    __path__.append(str(_src_core))

