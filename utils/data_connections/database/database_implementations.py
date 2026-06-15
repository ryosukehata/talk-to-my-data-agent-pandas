import sys
from importlib import import_module

_module = import_module("core.data_connections.database.database_implementations")
sys.modules[__name__] = _module
