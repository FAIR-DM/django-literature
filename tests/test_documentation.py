"""SC-004 documentation tests.

Programmatically inspects all public classes and functions in the core
``literature`` modules to assert every public interface has a non-empty
``__doc__`` string. Also verifies that every ``Item`` field that corresponds
to a CSL JSON key has non-empty ``help_text``.

This test file enforces SC-004 ("0 undocumented public interfaces") without
relying purely on manual audit.
"""

from __future__ import annotations

import inspect

import pytest

# ---------------------------------------------------------------------------
# Module-level symbol discovery
# ---------------------------------------------------------------------------

# Internal helper: collect (label, obj) pairs for all public class/function
# members of a module (only those defined in that module).


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


# ---------------------------------------------------------------------------
# Collect symbols from all target modules
# ---------------------------------------------------------------------------


def _gather_symbols():
    """Return list of (label, obj) for all public symbols in literature.*."""
    from literature import choices, converters, models
    from literature.utils import date as date_utils

    symbols = []
    for mod in (models, converters, choices, date_utils):
        prefix = "literature"
        for label, obj in _public_classes_and_functions(mod):
            symbols.append((label, obj))
            if inspect.isclass(obj):
                for method_label, method in _public_methods(obj, prefix):
                    symbols.append((method_label, method))
    return symbols


_ALL_SYMBOLS = _gather_symbols()


@pytest.mark.parametrize("label,obj", _ALL_SYMBOLS, ids=[s[0] for s in _ALL_SYMBOLS])
def test_public_symbol_has_docstring(label, obj):
    """Every public class and function must have a non-empty __doc__."""
    assert obj.__doc__, f"{label} is missing a docstring"


# ---------------------------------------------------------------------------
# Item field help_text coverage
# ---------------------------------------------------------------------------

# Fields NOT expected to have CSL JSON help_text (internal / Django metadata)
_NON_CSL_FIELDS = frozenset(
    {
        "id",
        "created",
        "modified",
        # Reverse relations added by related models
        "item_names",
        "itemname_set",
        "itemdate_set",
        "itemidentifier_set",
        "item_dates",
        "item_identifiers",
    }
)


def _item_csl_fields():
    """Yield (field_name,) for all Item fields that should have CSL help_text."""
    from literature.models import Item

    for field in Item._meta.get_fields():
        if field.name in _NON_CSL_FIELDS:
            continue
        # Only concrete fields (not reverse relations)
        if not hasattr(field, "help_text"):
            continue
        yield (field.name,)


@pytest.mark.parametrize("field_name", [f[0] for f in _item_csl_fields()])
def test_item_field_has_help_text(field_name):
    """Every CSL JSON Item field must have non-empty help_text."""
    from literature.models import Item

    field = Item._meta.get_field(field_name)
    assert field.help_text, f"Item.{field_name} is missing help_text describing its CSL JSON mapping"
