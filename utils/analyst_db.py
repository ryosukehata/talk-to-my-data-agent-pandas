import sys
from importlib import import_module

_module = import_module("core.analyst_db")
sys.modules[__name__] = _module
