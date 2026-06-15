import sys
from importlib import import_module

_module = import_module("core.customize.rest_api")
sys.modules[__name__] = _module
