import sys
from importlib import import_module

_module = import_module("core.customize.infrastructure.analyst_db.data_retriever")
sys.modules[__name__] = _module
