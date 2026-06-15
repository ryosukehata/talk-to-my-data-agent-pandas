import sys
from importlib import import_module

_module = import_module("core.datarobot_client")
sys.modules[__name__] = _module
