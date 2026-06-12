import sys
from importlib import import_module

_module = import_module("core.customize.domain.report.service_interface")
sys.modules[__name__] = _module
