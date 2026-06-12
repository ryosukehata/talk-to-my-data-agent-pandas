import sys
from importlib import import_module

_module = import_module("core.data_analyst_telemetry")
sys.modules[__name__] = _module
