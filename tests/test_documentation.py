"""Tests that every public class and function in the core modules has a docstring."""

from __future__ import annotations

import inspect

import pytest


def _public_classes_and_functions(module):
    """Yield (qualified_name, obj) for public classes and functions in *module*."""
    mod_name = module.__name__
    for name, obj in inspect.getmembers(module):
        if name.startswith("_"):
            continue
        if inspect.isclass(obj) or inspect.isfunction(obj):
            # Only include objects actually defined in this module
            defined_in = getattr(obj, "__module__", None)
            if defined_in and not defined_in.startswith(mod_name.split(".")[0]):
                continue
            yield f"{mod_name}.{name}", obj


def _public_methods(cls, module_prefix):
    """Yield (qualified_name, method) for public methods defined on *cls*."""
    for name, obj in inspect.getmembers(cls, predicate=inspect.isfunction):
        if name.startswith("_"):
            continue
        defined_in = getattr(obj, "__module__", None)
        if defined_in and not defined_in.startswith(module_prefix):
            continue
        yield f"{cls.__module__}.{cls.__name__}.{name}", obj


def _gather_symbols():
    """Return list of (label, obj) for all public symbols in literature.*."""
    from literature import choices, converters, importers, models
    from literature.utils import date as date_utils

    symbols = []
    for mod in (models, converters, choices, date_utils, importers):
        prefix = "literature"
        for label, obj in _public_classes_and_functions(mod):
            symbols.append((label, obj))
            if inspect.isclass(obj):
                for method_label, method in _public_methods(obj, prefix):
                    symbols.append((method_label, method))
    return symbols


_ALL_SYMBOLS = _gather_symbols()


class TestDocstringCoverage:
    @pytest.mark.parametrize(
        "label,obj", _ALL_SYMBOLS, ids=[s[0] for s in _ALL_SYMBOLS]
    )
    def test_public_symbol_has_docstring(self, label, obj):
        assert obj.__doc__, f"{label} is missing a docstring"
