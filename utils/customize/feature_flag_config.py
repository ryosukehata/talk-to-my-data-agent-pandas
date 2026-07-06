import sys
from importlib import import_module

_module = import_module("core.customize.feature_flag_config")
sys.modules[__name__] = _module
