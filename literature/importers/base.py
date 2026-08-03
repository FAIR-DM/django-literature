"""The format contract: what a bibliographic file syntax plugs in as.

See contracts/importers.md for the full contract. A format supplies only the file-to-entries
and entry-to-CSL-JSON stages (FR-003); nothing here gives it a route to the
stage that builds an ``Item``, and the contract offers no way to reach it.
"""

import abc
from collections.abc import Iterator
from typing import Any, ClassVar


class Format(abc.ABC):
    """A plug-in for one bibliographic file syntax, such as BibTeX or RIS.

    Registered under :attr:`name` (see :mod:`literature.importers.registry`).
    Has no member beyond the three below — building an ``Item`` from the CSL
    JSON a format produces is the runner's job, not the format's.
    """

    name: ClassVar[str]
    label: ClassVar[str]

    @abc.abstractmethod
    def parse(self, file) -> Iterator[Any]:
        """Yield this file's raw entries one at a time.

        An iterator, not a list — FR-024 depends on it, and returning a
        list would quietly make one-at-a-time consumption unmeetable from
        outside the format.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def to_csl_json(self, raw: Any) -> dict[str, Any]:
        """Turn one raw entry into a CSL JSON dict.

        Raise :class:`~literature.importers.exceptions.SkipEntry` for an
        element the format recognises but that is not a bibliographic
        record, or :class:`~literature.importers.exceptions.EntryError` for
        one that is bad. A :class:`~django.core.exceptions.ValidationError`
        may also be left to escape, whether raised directly or by way of
        ``from_csl_json`` once the runner calls it with the returned dict.
        """
        raise NotImplementedError

    def handle_for(self, raw: Any) -> str | None:
        """The source's own name for this entry, where the syntax has one.

        A BibTeX cite key, an RIS record number. ``None`` by default,
        since not every syntax has one and requiring it would push formats
        into inventing identifiers.
        """
        return None
