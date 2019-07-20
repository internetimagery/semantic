""" Convenience CLI """

from __future__ import print_function

import sys
import argparse
import surface
import logging
import functools

try:
    import cPickle as pickle
except ImportError:
    import pickle


LOG = logging.getLogger(__name__)
LOG.addHandler(logging.StreamHandler(sys.stderr))


def run_dump(args):
    modules = (
        set(r for m in args.modules for r in surface.recurse(m))
        if args.recurse
        else args.modules
    )

    module_api = {}
    for module in modules:
        try:
            api = surface.get_api(module)
        except ImportError:
            LOG.info(
                "Failed to import '{}'.\nIs the module in your PYTHONPATH?".format(
                    module
                )
            )
            return 1
        else:
            module_api[module] = api

    if not args.output:
        for mod, api in module_api.items():
            sys.stdout.write("[{}]\n".format(mod))
            sys.stdout.write(surface.format_api(api, "    "))
        return 0

    with open(args.output, "wb") as handle:
        pickle.dump(module_api, handle)
    LOG.info("Saved API to {}".format(args.output))
    return 0


def run_compare(args):
    with open(args.old, "rb") as handle:
        old_data = pickle.load(handle)

    with open(args.new, "rb") as handle:
        new_data = pickle.load(handle)

    highest_level = semantic.PATCH
    changes = surface.compare(old_data, new_data)
    for level, note in changes:
        if args.verbose:
            LOG.info(note)
        if level == semantic.MAJOR:
            highest_level = level
        elif level == semantic.MINOR and highest_level != semantic.MAJOR:
            highest_level = level
    if args.bump:
        sys.stdout.write(semantic.bump_semantic_version(highest_level, args.bump))
    else:
        sys.stdout.write(highest_level)


parser = argparse.ArgumentParser(
    description="Generate representations of publicly exposed Python API's."
)
subparsers = parser.add_subparsers()

dump_parser = subparsers.add_parser("dump", help="Store surface API in a file.")
dump_parser.add_argument("-o", "--output", help="File to store API into.")
dump_parser.add_argument(
    "modules", nargs="+", help="Full import path to module eg: mymodule.submodule"
)
dump_parser.add_argument(
    "-r", "--recurse", action="store_true", help="Recusively read submodules too."
)
dump_parser.set_defaults(func=run_dump)

compare_parser = subparsers.add_parser(
    "compare", help="Compare two API's and suggest a semantic version."
)
compare_parser.add_argument("old", help="Path to original API file.")
compare_parser.add_argument("new", help="Path to new API file.")
compare_parser.add_argument("-v", "--verbose", help="Display more information about the changes detected.")
compare_parser.add_argument("-b", "--bump", help="Instead of semantic level, return the version bumped.")
compare_parser.set_defaults(func=run_compare)

args = parser.parse_args()
sys.exit(args.func(args))
