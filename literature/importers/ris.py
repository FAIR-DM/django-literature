"""Reading RIS files into the catalogue.

The second concrete format behind the import contract (spec 005), following the shape
:class:`~literature.importers.bibtex.BibTeXFormat` established: it supplies only the two stages
a format owns, :meth:`~RISFormat.parse` and :meth:`~RISFormat.to_csl_json`; the workflow,
atomicity, per-entry reporting and dry runs all come from
:class:`~literature.importers.base.BibFormat` unchanged.

This module is the foundational phase only — :class:`RISParser` and the :class:`RISFormat`
skeleton. There is no RIS-to-CSL mapping yet: that is US-1 (issue #36). Until it lands, only a
file with no entries (an empty file, or one holding nothing but header material) converts
cleanly; a real entry's :meth:`~RISFormat.to_csl_json` raises, and is reported as a failed entry
like any other conversion the contract cannot complete (plan.md "Story boundaries").

One format reads EndNote, Web of Science and Scopus alike, with no producer detection (FR-029):
the parser reads what the primary RIS specification defines, and the tags that only some
producers use are read by the tags themselves rather than by which tool wrote the file.

The parser is hand-rolled rather than built on ``rispy``: see research.md R1 and decisions.md D11
for why, checked empirically rather than assumed.
"""

import dataclasses
import re
from collections.abc import Iterator
from typing import Any, ClassVar

from django.utils.translation import gettext_lazy as _

from literature.importers.base import BibFormat
from literature.importers.exceptions import ParseError, SkipEntry


@dataclasses.dataclass(frozen=True)
class RISEntry:
    """One RIS entry recovered from a file: its tags in source order, its position among the
    entries this parser has yielded, and the line its opening ``TY`` tag was found on.

    ``tags`` is an ordered sequence of ``(tag, value)`` pairs rather than a dict, because a
    repeatable tag (``AU``, ``KW``, ...) legitimately appears more than once — see
    :attr:`RISParser.REPEATABLE_TAGS`.
    """

    tags: tuple[tuple[str, str], ...]
    index: int
    start_line: int

    def values(self, tag: str) -> list[str]:
        """Every value this entry carries under ``tag``, in source order."""
        return [value for t, value in self.tags if t == tag]


class RISParser:
    """Reads one ``.ris`` file into :class:`RISEntry` objects, one at a time.

    A generator, not a list builder (FR-004): the whole file's entries are never materialised
    before the first is available, which is what lets a caller consume one entry from a
    several-hundred-entry file and leave the rest unread.

    Expects ``file`` opened in **binary** mode. Decoding is this parser's own job — ``utf-8-sig``,
    so a byte-order mark is silently absorbed rather than becoming part of the first tag's value
    (research.md R1) — because naming the attempted encoding and the byte offset on failure
    (FR-034) needs the raw bytes, not whatever a caller's own text-mode decoding already turned
    them into (decisions.md D19).
    """

    #: Tolerant of the single-space and double-space-after-dash variants real producers emit
    #: (plan.md "The parser"; research.md R2 documents the two-space form as the specification's
    #: own, and real exports vary).
    _TAG_RE: ClassVar[re.Pattern[str]] = re.compile(r"^([A-Z][A-Z0-9])\s{0,2}-\s?(.*)$")

    #: An untagged line following one of these tags becomes another value; following any other
    #: tag, it is a continuation joined onto the previous value with a single space (FR-007,
    #: amended — see decisions.md D12, D20). Repeatability is RIS syntax, decidable from the tag
    #: alone, and has nothing to do with the CSL mapping, so it lives on the parser rather than on
    #: the (not-yet-built) mapping tables.
    REPEATABLE_TAGS: ClassVar[frozenset[str]] = frozenset({"AU", "A1", "A2", "A3", "A4", "ED", "KW", "UR", "SN", "N1"})

    def parse(self, file) -> Iterator[RISEntry | str]:
        """Yield this file's entries, one at a time, in source order.

        Header material — everything before the first ``TY`` tag — is yielded once, as a plain
        ``str``, immediately before the first entry (plan.md "How the skipped header is
        signalled"); :meth:`RISFormat.to_csl_json` raises
        :class:`~literature.importers.exceptions.SkipEntry` for it, the same pattern
        ``bibtex.py`` uses for a comment or preamble. A file with no header material at all
        yields no such sentinel (decisions.md D17).

        Raises :class:`~literature.importers.exceptions.ParseError` — never lets a decoding or
        framing failure escape raw — when the file cannot be decoded, when it carries RIS tag
        lines but no ``TY`` anywhere, or when it carries no recognisable tag lines at all. An
        empty or whitespace-only file is not an error: it yields nothing (spec Edge Cases).
        """
        raw = file.read()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ParseError(
                _("Could not decode this file as {encoding}: invalid byte at offset {offset}.").format(
                    encoding=exc.encoding, offset=exc.start
                )
            ) from exc

        if not text.strip():
            return

        lines = text.splitlines()

        has_tag_line = False
        has_ty = False
        for line in lines:
            match = self._TAG_RE.match(line)
            if match:
                has_tag_line = True
                if match.group(1) == "TY":
                    has_ty = True
                    break

        if not has_tag_line:
            raise ParseError(_("No RIS tag lines found. Is this an RIS file, or in an unexpected encoding?"))
        if not has_ty:
            raise ParseError(_("This file carries RIS tags but no 'TY' (reference type) tag anywhere."))

        yield from self._entries(lines)

    def _entries(self, lines: list[str]) -> Iterator[RISEntry | str]:
        """The real framing pass: open at ``TY``, close at ``ER`` or the next ``TY`` (FR-006)."""
        header: list[str] = []
        pairs: list[list[str]] = []
        start_line = 0
        header_yielded = False
        index = 0

        for line_no, line in enumerate(lines, start=1):
            match = self._TAG_RE.match(line)

            if match is None:
                if pairs:
                    continue  # untagged-line continuation is T007's job
                if not header_yielded:
                    header.append(line)
                continue

            tag, value = match.group(1), match.group(2)

            if tag == "TY":
                if pairs:
                    yield RISEntry(tags=tuple((t, v) for t, v in pairs), index=index, start_line=start_line)
                    index += 1
                elif not header_yielded:
                    text = "\n".join(header).strip()
                    if text:
                        yield text
                header_yielded = True
                pairs = [[tag, value]]
                start_line = line_no
                continue

            if tag == "ER":
                if pairs:
                    yield RISEntry(tags=tuple((t, v) for t, v in pairs), index=index, start_line=start_line)
                    index += 1
                    pairs = []
                continue

            if pairs:
                pairs.append([tag, value])
            elif not header_yielded:
                header.append(line)
            # else: a tag block after the first entry with no TY -- out of the foundational
            # phase's scope (US-2, T021); dropped rather than guessed at (decisions.md D18).

        if pairs:
            yield RISEntry(tags=tuple((t, v) for t, v in pairs), index=index, start_line=start_line)


class RISFormat(BibFormat):
    """Reads ``.ris`` files, from EndNote, Web of Science and Scopus alike.

    The foundational-phase skeleton: wired into ``DEFAULTS`` and the ``literature`` namespace,
    with a working :class:`RISParser` behind it, but no RIS-to-CSL mapping yet (US-1, issue #36).
    A file with no entries converts cleanly; a real entry's conversion is not yet implemented.
    """

    name = "ris"
    label = _("RIS")

    def parse(self, file) -> Iterator[RISEntry | str]:
        return RISParser().parse(file)

    def to_csl_json(self, raw: RISEntry | str) -> dict[str, Any]:
        if isinstance(raw, str):
            raise SkipEntry
        raise NotImplementedError(
            "RIS entry mapping lands with US-1 (issue #36); the foundational phase builds only "
            "the parser and the class skeleton."
        )
