"""The test-only format used to exercise the import contract (US1).

Real bibliographic syntaxes arrive with BibTeX (#22) and RIS (#23). Until
then, this module stands in for one: a small ``BibFormat`` whose entries are
built from raw dicts tagged by ``kind``, so a test can ask for exactly the
mix of good, unreadable, skippable, and part-way-failing entries a scenario
needs (spec.md "Independent Test") without any real file syntax getting in
the way.

Each factory below returns a *class*, not an instance — the same shape
:func:`~literature.importers.config.get_format` returns (US3) — so a test
calls ``some_format().import_file(...)``, building a fresh instance with the
entries and any observer closed over. That keeps every test's format
independent of every other's.
"""

import pytest

from literature.importers.base import BibFormat
from literature.importers.exceptions import EntryError, ParseError, SkipEntry


def make_echo_format(entries, *, on_yield=None, format_name="echo"):
    """Build a ``BibFormat`` that yields ``entries`` one at a time.

    Each raw entry is a dict. ``to_csl_json`` dispatches on its ``kind``:

    - absent, or ``"good"`` — the dict itself, minus ``kind`` and
      ``handle``, is a CSL JSON entry ready for ``from_csl_json``.
    - ``"skip"`` — raises :class:`SkipEntry`, with ``reason`` as its note.
    - ``"entry_error"`` — raises :class:`EntryError` with ``reason``.

    Any other raw dict (for instance one with a ``type`` that is not a
    recognised CSL type, or a ``custom`` block built to collide with
    itself) is passed through unchanged, so ``from_csl_json`` is what
    rejects it — exercising "lets a ValidationError out"
    (contracts/importers.md).

    ``on_yield``, when given, is called with each raw entry immediately
    before it is yielded — a hook for observing how the runner consumes
    the iterator (FR-024, T012), since a generator only advances past a
    ``yield`` when its consumer asks for the next value.

    ``handle_for`` reads the raw dict's own ``"handle"`` key, so a test
    can mix entries that carry one with entries that do not (FR-009).
    """

    class _EchoFormat(BibFormat):
        label = "Echo (test-only)"

        def parse(self, file):
            for raw in entries:
                if on_yield is not None:
                    on_yield(raw)
                yield raw

        def to_csl_json(self, raw):
            kind = raw.get("kind", "good")
            if kind == "skip":
                raise SkipEntry(raw.get("reason", ""))
            if kind == "entry_error":
                raise EntryError(raw.get("reason", "bad entry"))
            return {key: value for key, value in raw.items() if key not in ("kind", "handle")}

        def handle_for(self, raw):
            return raw.get("handle")

    _EchoFormat.name = format_name
    return _EchoFormat


def make_failing_parse_format(entries, reason="bad entry", format_name="failing-parse"):
    """Build a ``BibFormat`` that yields ``entries`` and then raises ``EntryError``.

    ``parse`` may raise ``EntryError`` as well as ``ParseError``
    (exceptions.py, contracts/importers.md) — a syntax can recognise that
    an entry is bad before anything tries to convert it. The runner has to
    report that as a failure rather than let it escape (FR-014).
    """

    class _FailingParseFormat(BibFormat):
        label = "Failing parse (test-only)"

        def parse(self, file):
            yield from entries
            raise EntryError(reason)

        def to_csl_json(self, raw):
            return {key: value for key, value in raw.items() if key not in ("kind", "handle")}

    _FailingParseFormat.name = format_name
    return _FailingParseFormat


def make_bad_handle_format(entries, reason="cannot read this entry's key", format_name="bad-handle"):
    """Build a ``BibFormat`` whose ``handle_for`` raises on untrusted content.

    ``handle_for`` reads the same raw entry as ``to_csl_json``, so a
    malformed entry can break it too (FR-023). The entry is still reported,
    without a handle.
    """

    class _BadHandleFormat(BibFormat):
        label = "Bad handle (test-only)"

        def parse(self, file):
            yield from entries

        def to_csl_json(self, raw):
            return {key: value for key, value in raw.items() if key not in ("kind", "handle")}

        def handle_for(self, raw):
            raise EntryError(reason)

    _BadHandleFormat.name = format_name
    return _BadHandleFormat


def make_unparseable_format(reason="not this format", format_name="unparseable"):
    """Build a ``BibFormat`` whose ``parse`` cannot read the file at all.

    ``parse`` is written as a generator (the unreachable ``yield`` after
    the ``raise`` is what makes it one) so the ``ParseError`` fires only
    when the runner starts consuming it, matching how a format that
    recovers a few entries before truncation would also raise mid-stream.
    """

    class _UnparseableFormat(BibFormat):
        label = "Unparseable (test-only)"

        def parse(self, file):
            raise ParseError(reason)
            yield  # pragma: no cover - unreachable, keeps this a generator function

        def to_csl_json(self, raw):
            raise AssertionError("to_csl_json must not be called when parse() cannot yield an entry")

    _UnparseableFormat.name = format_name
    return _UnparseableFormat


class DuplicateCustomIdentifier(dict):
    """A ``custom`` block standing in for two identifiers of the same type.

    A real CSL JSON dict cannot carry a duplicate key — Python's own
    ``dict`` forbids it, so no format could ever build one from real file
    content. This is a test-only stand-in for the database race
    research.md R2 verified directly: two writes for the same
    ``(item, type)`` reaching ``ItemIdentifier.save()`` before either's
    uniqueness check has seen the other, which is what turns a per-entry
    failure into a genuine ``IntegrityError`` rather than the
    ``ValidationError`` ``full_clean()`` normally catches first.

    Needs ``ItemIdentifier.full_clean`` disabled to reach the database at
    all — see the ``bypass_identifier_validation`` fixture below. With
    validation intact, the second write is refused before either the
    savepoint or the database ever sees it, which is the ordinary,
    already-covered failure path.
    """

    def __init__(self, key="dup-id"):
        super().__init__({key: "AAA"})
        self._key = key

    def items(self):
        return [(self._key, "AAA"), (self._key, "BBB")]


@pytest.fixture
def bypass_identifier_validation(monkeypatch):
    """Disable ``ItemIdentifier.full_clean`` for one test.

    Lets a :class:`DuplicateCustomIdentifier` reach the database as a real
    ``IntegrityError`` instead of being refused earlier as a
    ``ValidationError`` (research.md R2). Scoped to the test via
    ``monkeypatch``, so no production code changes and nothing leaks
    beyond the test that asks for it.
    """
    from literature.models import ItemIdentifier

    monkeypatch.setattr(ItemIdentifier, "full_clean", lambda self, *args, **kwargs: None)


def make_skipping_handle_format(entries, format_name="skipping-handle"):
    """Build a ``BibFormat`` whose ``handle_for`` raises ``SkipEntry``.

    Out of contract — ``SkipEntry`` belongs to ``to_csl_json`` — but a format
    can reach for it anywhere, and when ``handle_for`` shared a block with
    ``to_csl_json`` the result was a good bibliographic record reported as
    deliberately skipped and stored nowhere.
    """

    class _SkippingHandleFormat(BibFormat):
        label = "Skipping handle (test-only)"

        def parse(self, file):
            yield from entries

        def to_csl_json(self, raw):
            return {key: value for key, value in raw.items() if key not in ("kind", "handle")}

        def handle_for(self, raw):
            raise SkipEntry("not a record, apparently")

    _SkippingHandleFormat.name = format_name
    return _SkippingHandleFormat


def make_raising_format(entries, exception, *, stage="to_csl_json", format_name="raising"):
    """Build a ``BibFormat`` that raises ``exception`` at ``stage``.

    For the exception types the contract does *not* name. A format is
    third-party code and ``from_csl_json`` is not defensive about the shape of
    the CSL JSON it is handed, so an import meets exceptions outside the
    contract's vocabulary and has to report them rather than let them out.
    """

    class _RaisingFormat(BibFormat):
        label = "Raising (test-only)"

        def parse(self, file):
            yield from entries
            if stage == "parse":
                raise exception

        def to_csl_json(self, raw):
            if stage == "to_csl_json":
                raise exception
            return {key: value for key, value in raw.items() if key not in ("kind", "handle")}

    _RaisingFormat.name = format_name
    return _RaisingFormat
