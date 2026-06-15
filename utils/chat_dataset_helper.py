import sys
from importlib import import_module

_module = import_module("core.chat_dataset_helper")
sys.modules[__name__] = _module
