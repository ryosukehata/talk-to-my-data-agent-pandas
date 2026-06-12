import sys
from importlib import import_module

_module = import_module("core.i18n")
sys.modules[__name__] = _module
