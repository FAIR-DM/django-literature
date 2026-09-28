"""Tests for ``literature/ui/staging.py``: the file a preview holds until it is confirmed.

Session scoping is the view's job and is tested in ``test_views.py``.
"""

import os
from datetime import timedelta

import pytest
from django.core.files.base import ContentFile
from django.utils import timezone

from literature.ui.staging import RETENTION_WINDOW, StagedUpload


@pytest.fixture
def staging(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    return StagedUpload()


class TestStagedUpload:
    def test_saving_returns_a_token_and_the_bytes_can_be_read_back(self, staging):
        token = staging.save(ContentFile(b"the file's own bytes", name="upload.bib"))
        assert token
        with staging.open(token) as handle:
            assert handle.read() == b"the file's own bytes"

    def test_reading_with_a_token_this_session_did_not_issue_returns_nothing(
        self, staging
    ):
        assert staging.open("not-a-token-anyone-issued") is None

    def test_a_staged_file_is_removed_on_discard(self, staging):
        token = staging.save(ContentFile(b"gone shortly", name="upload.bib"))
        staging.discard(token)
        assert staging.open(token) is None

    def test_discarding_a_token_that_was_never_staged_does_not_raise(self, staging):
        staging.discard("never-issued")

    def test_a_staged_file_older_than_the_retention_window_is_swept_and_a_fresh_one_is_not(
        self, staging
    ):
        stale_token = staging.save(ContentFile(b"stale", name="stale.bib"))
        fresh_token = staging.save(ContentFile(b"fresh", name="fresh.bib"))

        stale_path = staging.storage.path(f"{staging.directory}/{stale_token}")
        backdated = (
            timezone.now() - RETENTION_WINDOW - timedelta(minutes=1)
        ).timestamp()
        os.utime(stale_path, (backdated, backdated))

        staging.sweep()

        assert staging.open(stale_token) is None
        with staging.open(fresh_token) as handle:
            assert handle.read() == b"fresh"

    def test_sweeping_with_nothing_staged_yet_does_not_raise(self, staging):
        staging.sweep()

    def test_a_file_removed_while_the_sweep_is_walking_it_does_not_raise(self, staging):
        # Every entry to the import page sweeps, so two readers arriving at
        # once both walk the same directory. Whichever removes a stale file
        # first leaves the other holding a name that no longer resolves,
        # between the listing and the check on its age.
        token = staging.save(ContentFile(b"stale", name="stale.bib"))
        path = staging.storage.path(f"{staging.directory}/{token}")
        backdated = (
            timezone.now() - RETENTION_WINDOW - timedelta(minutes=1)
        ).timestamp()
        os.utime(path, (backdated, backdated))

        real_get_modified_time = staging.storage.get_modified_time

        def remove_it_first(name):
            os.remove(staging.storage.path(name))
            return real_get_modified_time(name)

        staging.storage.get_modified_time = remove_it_first
        try:
            staging.sweep()
        finally:
            del staging.storage.get_modified_time

    def test_a_token_is_not_derivable_from_the_files_contents_or_name(self, staging):
        # Two uploads sharing both a name and its bytes must still be issued
        # different tokens — a token derived from either would collide here.
        first = staging.save(ContentFile(b"identical bytes", name="same-name.bib"))
        second = staging.save(ContentFile(b"identical bytes", name="same-name.bib"))
        assert first != second
