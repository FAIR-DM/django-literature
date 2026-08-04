"""The import contract's public surface (FR-021, Article X), T019.

Article X requires every public name to be importable from the ``literature``
namespace. The established reading in this package is a named submodule — a
caller reaches the whole contract through ``literature.importers`` and never
imports ``literature.importers.runner`` or ``.registry`` directly
(research.md R3).

These tests exist so that a name added to a submodule later, and never
re-exported, is caught here rather than by whoever tries to import it.
"""

import importlib
import inspect

import pytest

import literature.importers as importers

#: Every name the contract publishes, and the submodule that defines it.
PUBLIC_SURFACE = {
    "Format": "literature.importers.base",
    "ImporterError": "literature.importers.exceptions",
    "SkipEntry": "literature.importers.exceptions",
    "EntryError": "literature.importers.exceptions",
    "ParseError": "literature.importers.exceptions",
    "UnknownFormat": "literature.importers.exceptions",
    "FormatAlreadyRegistered": "literature.importers.exceptions",
    "register": "literature.importers.registry",
    "get_format": "literature.importers.registry",
    "available_formats": "literature.importers.registry",
    "Outcome": "literature.importers.results",
    "EntryResult": "literature.importers.results",
    "ImportResult": "literature.importers.results",
    "import_file": "literature.importers.runner",
}


class TestPublicSurface:
    def test_all_lists_exactly_the_documented_surface(self):
        """``__all__`` and the contract agree, in both directions.

        A name added to ``__all__`` but not to the contract fails here just as
        loudly as one added to the contract and never exported.
        """
        assert set(importers.__all__) == set(PUBLIC_SURFACE)

    @pytest.mark.parametrize("module", sorted(set(PUBLIC_SURFACE.values())))
    def test_every_public_name_a_submodule_defines_is_exported(self, module):
        """The half a hand-written list cannot catch.

        Both assertions above are derived from ``PUBLIC_SURFACE``, so a name
        added to ``registry.py`` and left out of *both* ``__all__`` and this
        file passes them without complaint — which is exactly the omission the
        guard is for. This one reads the submodules instead: anything they
        define without a leading underscore is public by Python's own
        convention, and must be reachable from the package (FR-021).
        """
        submodule = importlib.import_module(module)
        defined_here = {
            name
            for name, value in vars(submodule).items()
            if not name.startswith("_")
            and getattr(value, "__module__", None) == module
            and (inspect.isclass(value) or inspect.isfunction(value))
        }

        assert defined_here <= set(importers.__all__)

    @pytest.mark.parametrize("name", sorted(PUBLIC_SURFACE))
    def test_name_is_importable_from_the_package(self, name):
        """FR-021: reachable as ``literature.importers.<name>``."""
        assert hasattr(importers, name)

    @pytest.mark.parametrize(("name", "module"), sorted(PUBLIC_SURFACE.items()))
    def test_re_export_is_the_submodule_object_itself(self, name, module):
        """Not a copy, not a wrapper — the same object, so ``isinstance`` and
        ``except`` clauses behave identically whichever route a caller took.
        """
        assert getattr(importers, name) is getattr(importlib.import_module(module), name)
