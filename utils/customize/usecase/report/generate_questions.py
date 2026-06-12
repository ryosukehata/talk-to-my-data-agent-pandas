import sys
from importlib import import_module

_module = import_module("core.customize.usecase.report.generate_questions")
sys.modules[__name__] = _module
