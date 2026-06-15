import sys
from importlib import import_module

_module = import_module("core.customize.infrastructure.chat.chat_executor")
sys.modules[__name__] = _module
