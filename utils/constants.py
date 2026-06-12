import sys
from importlib import import_module

_module = import_module("core.constants")
sys.modules[__name__] = _module
