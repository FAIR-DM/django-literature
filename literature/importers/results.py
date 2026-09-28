"""What an import reports back.

One :class:`EntryResult` per entry the format found, collected into one
:class:`ImportResult`. This is the whole reporting surface: a caller learns what
happened to every entry by reading these objects, never by comparing a count of
inputs against a count of stored items and never by reading the log.
"""

from dataclasses import dataclass, field

from django.db import models
from django.utils.translation import gettext_lazy as _


class Outcome(models.TextChoices):
    """What became of one entry.

    There is deliberately no "updated": matching an entry to a record already
    stored is a separate problem, and a value nothing can produce is
    speculation. A later feature that makes that judgement reports it as
    ``SKIPPED``.
    """

    CREATED = "created", _("Created")
    SKIPPED = "skipped", _("Skipped")
    FAILED = "failed", _("Failed")


@dataclass(frozen=True)
class EntryResult:
    """The fate of a single entry.

    Attributes:
        outcome: What became of the entry.
        index: Zero-based position among the entries the format found. Always
            present, and assigned by the runner rather than the format.
        handle: The source's own name for this entry — a BibTeX cite key, an RIS
            record number — where the syntax has one. ``None`` when it does not.
        item: The stored ``Item``, on a real run that created one. ``None`` for
            skipped and failed entries, and for every entry of a dry run, whose
            rows do not survive the transaction that made them.
        reason: Why the entry failed, or what was recognised but not stored
            for a skipped entry. Required for ``FAILED``, optional for
            ``SKIPPED``, and refused for ``CREATED``.

    Raises:
        ValueError: If a failure carries no reason, or a created entry carries one.
    """

    outcome: Outcome
    index: int
    handle: str | None = None
    item: object | None = None
    reason: str | None = None

    def __post_init__(self):
        """Refuse a reason that does not fit the outcome, and resolve lazy text."""
        # A blank reason counts as missing: an exception raised with no message
        # gives ``str(exc) == ""``, the same silent drop one step further along.
        if self.outcome == Outcome.FAILED and not (self.reason or "").strip():
            raise ValueError("a failed entry result must carry a reason")
        if self.outcome == Outcome.CREATED and self.reason is not None:
            raise ValueError("only a failed or skipped entry result may carry a reason")
        if self.reason is not None:
            # Resolve lazy translations now, while the active language is right.
            object.__setattr__(self, "reason", str(self.reason))


@dataclass(frozen=True)
class ImportResult:
    """The report from one import run.

    Attributes:
        entries: One result per entry the format found, in the order they occur
            in the source file, each appearing exactly once.
        dry_run: Whether this run was a rehearsal that wrote nothing.
        format_name: The registered name used, when the import was run by name.
    """

    entries: list[EntryResult] = field(default_factory=list)
    dry_run: bool = False
    format_name: str | None = None

    def __iter__(self):
        """Iterate over the entry results in source order."""
        return iter(self.entries)

    def __len__(self):
        """Return the number of entries the format found."""
        return len(self.entries)

    def _with_outcome(self, outcome):
        return [entry for entry in self.entries if entry.outcome == outcome]

    @property
    def created(self):
        """Entries that became items."""
        return self._with_outcome(Outcome.CREATED)

    @property
    def skipped(self):
        """Elements the format recognised but that are not bibliographic records."""
        return self._with_outcome(Outcome.SKIPPED)

    @property
    def failed(self):
        """Entries that could not be stored, each carrying its reason."""
        return self._with_outcome(Outcome.FAILED)

    @property
    def ok(self):
        """True when nothing failed. An import of an empty file is ok."""
        return not self.failed
