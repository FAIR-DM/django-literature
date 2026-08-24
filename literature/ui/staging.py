"""Hold an uploaded file on disk between a preview and its confirmation (US-4,
decisions.md D16).

New module rather than an addition to ``views.py`` (Article XV): saving,
reading, discarding and sweeping a staged file share one subject — the file
itself — and none of it is a view or a form. What is deliberately *not*
here is any notion of which reader staged which file: that scoping is
FR-042's, and it is the session's job, held by the view that calls this
class, never carried into the token itself (see ``views.py``).
"""

from datetime import timedelta

from django.core.files.storage import default_storage
from django.utils import timezone
from django.utils.crypto import get_random_string

#: How long a staged file survives an import that never confirmed it,
#: before ``sweep()`` removes it. No requirement names a figure — FR-043
#: only requires that abandoned staging eventually go away — so this is a
#: judgement call, recorded as decisions.md D19: long enough that a reader
#: who previews a file and is called away mid-read can still come back the
#: same working day, short enough that an unauthenticated, unbounded upload
#: endpoint (D12) does not accumulate disk use indefinitely.
RETENTION_WINDOW = timedelta(hours=24)


class StagedUpload:
    """Save, open, discard and sweep a file staged for a later confirm.

    Backed by whatever Django's storage API resolves to (``default_storage``
    by default) rather than a hand-built path, so a project already
    configuring remote storage gets staging on it for free. Every staged
    file lives under :attr:`directory`, named by a random token that carries
    no relationship to the file's own name or contents (FR-042's other
    half: the token is only ever useful to whoever was handed it).
    """

    #: The storage sub-path staged files are kept under. Never the storage
    #: root — a project's own media may share the same storage backend, and
    #: this keeps a stale token from ever resolving to something the reader
    #: did not stage.
    directory = "literature-imports"

    def __init__(self, storage=None):
        self.storage = storage or default_storage

    def _name(self, token: str) -> str:
        return f"{self.directory}/{token}"

    def save(self, file) -> str:
        """Stage ``file`` and return the token that reads it back.

        The token is random (``get_random_string``, Django's own CSPRNG-backed
        helper), never derived from ``file``'s name or content — two
        uploads sharing both still get different tokens. The name actually
        used is whatever the storage backend reports back from ``save()``:
        on the vanishingly unlikely chance the token it was asked to save
        under collides with one already on disk, the storage layer picks a
        variant on it, and that is the name returned here, not the one
        requested.
        """
        token = get_random_string(43)
        saved_name = self.storage.save(self._name(token), file)
        return saved_name.rsplit("/", 1)[-1]

    def open(self, token):
        """The staged file's own reader, or ``None`` if ``token`` names nothing staged.

        A token nobody issued, or one whose file has already been discarded
        or swept, is indistinguishable here — either way there is nothing
        to confirm (FR-044).
        """
        name = self._name(token)
        if not self.storage.exists(name):
            return None
        return self.storage.open(name, "rb")

    def discard(self, token) -> None:
        """Remove the staged file for ``token``, if it is still there.

        Never raises for a token already gone — carrying out a confirm and
        then discarding is the ordinary path (FR-043), and a caller should
        not have to check first.
        """
        name = self._name(token)
        if self.storage.exists(name):
            self.storage.delete(name)

    def sweep(self) -> None:
        """Remove every staged file older than :data:`RETENTION_WINDOW` (FR-043).

        Quietly does nothing if :attr:`directory` does not exist yet — the
        common case, since it is created lazily by the first :meth:`save`.
        """
        try:
            _, names = self.storage.listdir(self.directory)
        except FileNotFoundError:
            return

        cutoff = timezone.now() - RETENTION_WINDOW
        for name in names:
            full_name = self._name(name)
            if self.storage.get_modified_time(full_name) < cutoff:
                self.storage.delete(full_name)
