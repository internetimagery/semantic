""" Traverse an API heirarchy """


# TODO: import module by name
# TODO: get its global name, and path
# TODO: cache path names to module name for efficiency

# TODO: walk through everything it exposes at the top level
# TODO: eg: names not starting with underscores
# TODO: or anything in the __all__ variable.

# TODO: create a simplified representation of the signatures found (names and types)

# BONUS: collect type information as part of the signatures
# BONUS: traverse heirarchy for specified types, recursively getting their api
# BONUS: so later a type can be compared by value, not just name

import re
import logging
import os.path
import inspect
import sigtools
from surface._base import *
from surface._type import get_type, get_type_func
from importlib import import_module

if False:  # type checking
    from typing import List, Set, Any, Iterable

__all__ = ["recurse", "traverse"]

LOG = logging.getLogger(__name__)

import_reg = re.compile(r"__init__\.(py[cd]?|so)$")


def recurse(name):  # type: (str) -> List[str]
    """ Given a module path, return paths to its children. """

    stack = [name]
    paths = []

    while stack:
        import_name = stack.pop()
        module = import_module(import_name)
        paths.append(import_name)
        try:
            module_path = module.__file__
        except AttributeError:
            continue

        if not import_reg.search(module_path):
            paths.append(import_name)
            continue

        package = os.path.dirname(module_path)
        submodules = os.listdir(package)
        for submodule in submodules:
            if submodule.startswith("_"):
                pass
            elif submodule.endswith(".py"):
                paths.append("{}.{}".format(import_name, submodule[:-3]))
            elif os.path.isfile(os.path.join(package, submodule, "__init__.py")):
                stack.append("{}.{}".format(import_name, submodule))
    return paths


def traverse(obj, exclude_modules=False):  # type: (Any, bool) -> Iterable[Any]
    """ Entry point to generating an API representation. """
    attributes = [attr for attr in inspect.getmembers(obj) if is_public(attr[0])]
    # __all__ attribute restricts import with *,
    # and displays what is intended to be public
    whitelist = getattr(obj, "__all__", [])
    if whitelist:
        attributes = [attr for attr in attributes if attr[0] in whitelist]

    # Sort the attributes by name for readability, and diff-ability (is that a word?)
    attributes.sort(key=lambda a: a[0])

    # Walk the surface of the object, and extract the information
    for name, value in attributes:
        if not name:
            continue
        # TODO: How to ensure we find the original classes and methods, and not wrappers?
        # TODO: Handle recursive endless looping traversal.

        try:
            if inspect.ismodule(value):
                if exclude_modules:
                    continue
                yield handle_module(name, value)
            elif inspect.isclass(value):
                yield handle_class(name, value)
            # Python2
            elif inspect.ismethod(value):
                yield handle_method(name, value)
            elif inspect.isfunction(value):
                # python3
                if inspect.isclass(obj):
                    yield handle_method(name, value)
                else:
                    yield handle_function(name, value)
            elif name != "__init__":
                yield handle_variable(name, value)
        except SyntaxError as err:
            LOG.warn("Failed to parse {} {}.\n{}".format(name, value, err))


def handle_function(name, value):  # type: (str, Any) -> Func
    sig = sigtools.signature(value)
    param_types, return_type = get_type_func(value)
    return Func(
        name,
        tuple(
            Arg(
                n,
                t,
                convert_arg_kind(str(p.kind))
                | (0 if p.default is sig.empty else DEFAULT),
            )
            for (n, p), t in zip(sig.parameters.items(), param_types)
        ),
        return_type,
    )


def handle_method(name, value):  # type: (str, Any) -> Func
    sig = sigtools.signature(value)
    params = list(sig.parameters.items())
    param_types, return_type = get_type_func(value)
    if not "@staticmethod" in inspect.getsource(value):
        params = params[1:]
        param_types = param_types[1:]
    return Func(
        name,
        tuple(
            Arg(
                n,
                t,
                convert_arg_kind(str(p.kind))
                | (0 if p.default is sig.empty else DEFAULT),
            )
            for (n, p), t in zip(sig.parameters.items(), param_types)
        ),
        return_type,
    )


def handle_class(name, value):  # type: (str, Any) -> Class
    return Class(name, tuple(traverse(value)))


def handle_variable(name, value):  # type: (str, Any) -> Var
    return Var(name, get_type(value))


def handle_module(name, value):  # type: (str, Any) -> Module
    return Module(name, value.__name__, tuple(traverse(value)))


def is_public(name):  # type: (str) -> bool
    return name == "__init__" or not name.startswith("_")


def convert_arg_kind(kind):  # type: (str) -> int
    if kind == "POSITIONAL_ONLY":
        return POSITIONAL
    if kind == "KEYWORD_ONLY":
        return KEYWORD
    if kind == "POSITIONAL_OR_KEYWORD":
        return POSITIONAL | KEYWORD
    if kind == "VAR_POSITIONAL":
        return POSITIONAL | VARIADIC
    if kind == "VAR_KEYWORD":
        return KEYWORD | VARIADIC
    raise TypeError("Unknown type.")
