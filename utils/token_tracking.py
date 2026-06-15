import sys
from importlib import import_module

_module = import_module("core.token_tracking")
sys.modules[__name__] = _module
