import sys
from importlib import import_module

_module = import_module("core.customize.infrastructure.storage.report_storage")
sys.modules[__name__] = _module
