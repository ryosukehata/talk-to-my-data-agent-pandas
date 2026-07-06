import sys
from importlib import import_module

_module = import_module("core.customize.question_refiner.question_refiner")
sys.modules[__name__] = _module
