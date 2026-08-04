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

    Three values, every one of them reachable. Deliberately absent is anything
    meaning "updated": deciding that an entry matches a record already stored is
    a separate problem, and a vocabulary value nothing can produce is the
    speculation Article III rules out. When a later feature can make that
    judgement it reports its decisions as ``SKIPPED``, which needs no change
    here.
    """

    CREATED = "created", _("Created")
    SKIPPED = "skipped", _("Skipped")
    FAILED = "failed", _("Failed")


@dataclass(frozen=True)
class EntryResult:
    """The fate of a single entry.

    Args:
        outcome: What became of the entry.
        index: Zero-based position among the entries the format found. Always
            present, and assigned by the runner rather than the format.
        handle: The source's own name for this entry — a BibTeX cite key, an RIS
            record number — where the syntax has one. ``None`` when it does not.
        item: The stored ``Item``, on a real run that created one. ``None`` for
            skipped and failed entries, and for every entry of a dry run, whose
            rows do not survive the transaction that made them.
        reason: Why the entry failed. Set when, and only when, the outcome is
            ``FAILED``.

    Raises:
        ValueError: If a failure carries no reason, or a non-failure carries one.
    """

    outcome: Outcome
    index: int
    handle: str | None = None
    item: object | None = None
    reason: str | None = None

    def __post_init__(self):
        # A failure without a reason is exactly the silent drop this contract
        # exists to remove, so it is refused at construction rather than caught
        # later by whoever reads the report. Emptiness counts: an exception
        # raised with no message gives ``str(exc) == ""``, which is not None
        # and prints as a blank line — the same silent drop, one indirection
        # further along.
        if self.outcome == Outcome.FAILED and not (self.reason or "").strip():
            raise ValueError("a failed entry result must carry a reason")
        if self.outcome != Outcome.FAILED and self.reason is not None:
            raise ValueError("only a failed entry result may carry a reason")
        if self.reason is not None:
            # Reasons are built from lazy translations. Resolve now so the
            # result stays readable once the active language has moved on.
            object.__setattr__(self, "reason", str(self.reason))


@dataclass(frozen=True)
class ImportResult:
    """The report from one import run.

    Args:
        entries: One result per entry the format found, in the order they occur
            in the source file, each appearing exactly once.
        dry_run: Whether this run was a rehearsal that wrote nothing.
        format_name: The registered name used, when the import was run by name.
    """

    entries: list[EntryResult] = field(default_factory=list)
    dry_run: bool = False
    format_name: str | None = None

    def __iter__(self):
        return iter(self.entries)

    def __len__(self):
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
