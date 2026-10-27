"""Hold an uploaded file on disk between a preview and its confirmation."""

from datetime import timedelta

from django.core.files.storage import default_storage
from django.utils import timezone
from django.utils.crypto import get_random_string

#: How long a staged file survives an import that never confirmed it, before
#: ``sweep()`` removes it: long enough to come back the same working day.
RETENTION_WINDOW = timedelta(hours=24)


class StagedUpload:
    """Save, open, discard and sweep a file staged for a later confirm.

    Backed by whatever Django's storage API resolves to (``default_storage``
    by default) rather than a hand-built path, so a project already
    configuring remote storage gets staging on it for free. Every staged
    file lives under :attr:`directory`, named by a random token that carries
    no relationship to the file's own name or contents — the token is only
    ever useful to whoever was handed it (FS-011, #103). Which reader staged which
    file is the session's concern, held by the calling view, never the token's.

    Args:
        storage: The Django storage to stage on. Defaults to ``default_storage``.
    """

    #: The storage sub-path staged files are kept under, never the storage root,
    #: so a stale token cannot resolve to a project's own media.
    directory = "literature-imports"

    def __init__(self, storage=None):
        self.storage = storage or default_storage

    def _name(self, token: str) -> str:
        """Return the storage name a token's file is kept under.

        Args:
            token: The token issued by :meth:`save`.

        Returns:
            The path under :attr:`directory`.
        """
        return f"{self.directory}/{token}"

    def save(self, file) -> str:
        """Stage ``file`` and return the token that reads it back.

        The token is random (``get_random_string``, Django's own CSPRNG-backed
        helper), never derived from ``file``'s name or content. If the storage
        backend renames the file to avoid a collision, the token returned is
        the name it actually used.

        Args:
            file: The uploaded file to stage.

        Returns:
            The token that reads the file back.
        """
        token = get_random_string(43)
        # str(): the storage attribute is untyped, so mypy sees Any here.
        saved_name = str(self.storage.save(self._name(token), file))
        return saved_name.rsplit("/", 1)[-1]

    def open(self, token):
        """Open the staged file for reading.

        A token nobody issued, or one whose file has been discarded or swept,
        is indistinguishable here: either way there is nothing to confirm.

        Args:
            token: The token issued by :meth:`save`.

        Returns:
            A binary file object, or ``None`` if ``token`` names nothing staged.
        """
        name = self._name(token)
        if not self.storage.exists(name):
            return None
        return self.storage.open(name, "rb")

    def discard(self, token) -> None:
        """Remove the staged file for ``token``, if it is still there.

        Never raises for a token already gone: discarding after a confirm is the
        ordinary path, so a caller need not check first.

        Args:
            token: The token issued by :meth:`save`.
        """
        name = self._name(token)
        if self.storage.exists(name):
            self.storage.delete(name)

    def sweep(self) -> None:
        """Remove every staged file older than :data:`RETENTION_WINDOW`.

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
            try:
                if self.storage.get_modified_time(full_name) < cutoff:
                    self.storage.delete(full_name)
            except OSError:
                # Concurrent sweeps and confirms delete from under this listing;
                # a name that stopped resolving is already gone.
                continue
