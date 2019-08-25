""" Wrapping static ast objects """

if False:  # type checking
    from typing import *

import ast
import collections

from surface._base import UNKNOWN, PY2
from surface._item import Item


class AstItem(Item):

    wraps = None  # type: Any

    __slots__ = []  # type: ignore

    @classmethod
    def parse(cls, visitors, source):
        module = ast.parse(source)
        return cls.wrap(visitors, module)

    @classmethod
    def is_this_type(cls, item, parent):
        return isinstance(item, cls.wraps)


class ModuleAst(AstItem):

    wraps = ast.Module

    def get_children_names(self):
        return range(len(self.item.body))

    def get_child(self, index):
        return self.item.body[index].value


class SubscriptAst(AstItem):
    wraps = ast.Subscript

    def get_children_names(self):
        return ("value", "slice")

    def get_child(self, index):
        if index == "value":
            return self.item.value
        elif index == "slice":
            return self.item.slice
        else:
            raise KeyError("Index {} is not here.".format(index))


class SliceAst(AstItem):

    wraps = (ast.Index, ast.Slice, ast.ExtSlice)

    def get_children_names(self):
        return range(len(self._children()))

    def get_child(self, index):
        return self._children()[index]

    def _children(self):
        if isinstance(self.item, ast.Index):
            return [self.item.value]
        if isinstance(self.item, ast.ExtSlice):
            return self.item.dims
        children = []
        if self.item.lower:
            children.append(self.item.lower)
        if self.item.upper:
            children.append(self.item.upper)
        if self.item.step:
            children.append(self.item.step)
        return children


class TupleAst(AstItem):

    wraps = ast.Tuple

    def get_children_names(self):
        return range(len(self.item.elts))

    def get_child(self, index):
        return self.item.elts[index]


class AttributeAst(AstItem):

    wraps = ast.Attribute

    @property
    def name(self):
        return ".".join(reversed(self._walk(self.item)))

    def _walk(self, item, chain=None):
        if chain is None:
            chain = []
        if isinstance(item, ast.Attribute):
            chain.append(item.attr)
            self._walk(item.value, chain)
        elif isinstance(item, ast.Name):
            chain.append(item.id)
        else:
            raise TypeError("Unknown type {}".format(item))
        return chain


class NameAst(AstItem):

    wraps = ast.Name if PY2 else (ast.Name, ast.NameConstant)

    @property
    def name(self):
        if isinstance(self.item, ast.Name):
            return self.item.id
        return repr(self.item.value)


class EllipsisAst(AstItem):

    wraps = ast.Ellipsis


class UnknownAst(AstItem):
    @staticmethod
    def is_this_type(item, parent):
        return (
            isinstance(item, ast.UnaryOp)
            and isinstance(item.op, ast.Invert)
            and isinstance(item.operand, ast.Name)
            and item.operand.id == UNKNOWN[1:]
        )


if __name__ == "__main__":
    typestring = "typing.Dict[str, typing.List[None]]"

    visitors = [
        ModuleAst,
        SubscriptAst,
        NameAst,
        TupleAst,
        UnknownAst,
        AttributeAst,
        SliceAst,
        EllipsisAst,
    ]

    p = AstItem.parse(visitors, typestring)

    def walk(item):
        print(item, getattr(item, "name", ""))
        for child in item.values():
            walk(child)

    walk(p)
