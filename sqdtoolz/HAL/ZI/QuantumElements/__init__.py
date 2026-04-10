import pkgutil
import importlib
import inspect
import os

#WARNING: All classes/files should have unique names.
pkg_name = __name__
pkg_path = [os.path.dirname(__file__)]
__all__ = []
for loader, module_name, is_pkg in pkgutil.iter_modules(pkg_path):
    full_module_name = f".{module_name}"
    module = importlib.import_module(full_module_name, package=pkg_name)
    __all__.append(module_name)
    for name, obj in inspect.getmembers(module, inspect.isclass):
        # Only import classes defined in the module itself (not imported classes)
        if obj.__module__ == module.__name__:
            globals()[name] = obj
            __all__.append(name)
