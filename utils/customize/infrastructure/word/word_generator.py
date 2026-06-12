import sys
from importlib import import_module

_module = import_module("core.customize.infrastructure.word.word_generator")
sys.modules[__name__] = _module
