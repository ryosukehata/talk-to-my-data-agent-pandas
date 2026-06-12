import sys
from importlib import import_module

_module = import_module("core.api_exceptions")
sys.modules[__name__] = _module
