import sys
from importlib import import_module

_module = import_module("core.customize.csv_validator")
sys.modules[__name__] = _module
