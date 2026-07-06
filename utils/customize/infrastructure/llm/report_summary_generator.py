import sys
from importlib import import_module

_module = import_module("core.customize.infrastructure.llm.report_summary_generator")
sys.modules[__name__] = _module
