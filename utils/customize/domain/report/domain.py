import sys
from importlib import import_module

_module = import_module("core.customize.domain.report.domain")
sys.modules[__name__] = _module
