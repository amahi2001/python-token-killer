"""Minimizer registry — auto-imports all strategies."""

from ptk.minimizers._dict import DictMinimizer
from ptk.minimizers._list import ListMinimizer
from ptk.minimizers._code import CodeMinimizer
from ptk.minimizers._log import LogMinimizer
from ptk.minimizers._diff import DiffMinimizer
from ptk.minimizers._text import TextMinimizer

__all__ = [
    "DictMinimizer",
    "ListMinimizer",
    "CodeMinimizer",
    "LogMinimizer",
    "DiffMinimizer",
    "TextMinimizer",
]
