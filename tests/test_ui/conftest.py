"""Shared fixtures for the opt-in front end's tests."""

from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from literature.models import Item
from tests.factories import (
    ItemDateFactory,
    ItemFactory,
    ItemIdentifierFactory,
    ItemNameFactory,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture
def stage_import(client):
    """Return a function that submits a file to the import form and returns the response.

    With no ``content`` the upload is ``tests/data/<filename>``. Extra keyword arguments
    are posted as further form fields, e.g. ``skip_preview="on"``.
    """

    def stage(filename="publication.bib", format_name="bibtex", content=None, **fields):
        if content is None:
            content = (DATA_DIR / filename).read_bytes()
        elif isinstance(content, str):
            content = content.encode()
        upload = SimpleUploadedFile(filename, content)
        return client.post(
            reverse("literature:item-import"),
            {"format": format_name, "file": upload, **fields},
        )

    return stage


@pytest.fixture
def preview_import(client, stage_import):
    """Return a function that stages a file as ``stage_import`` does and returns its preview."""

    def preview(*args, **kwargs):
        stage_import(*args, **kwargs)
        return client.get(reverse("literature:item-import-preview"))

    return preview


@pytest.fixture
def populated_item(db):
    item = ItemFactory()
    ItemNameFactory(item=item)
    ItemDateFactory(item=item)
    ItemIdentifierFactory(item=item)
    return item


#: The four fields that are on ``Item`` but never on ``ItemForm``, shared
#: by ``test_fieldgroups.py`` (which checks the field-group partition against
#: it) and ``test_forms.py`` (which checks ``ItemForm`` itself against it).
#: ``categories`` and ``custom`` are excluded because the form never carries
#: them; ``created`` and ``modified`` because they are auto-managed
#: timestamps, not CSL variables.
EXCLUDED_FROM_FORM = frozenset({"categories", "custom", "created", "modified"})


def scalar_field_names():
    """Every concrete, non-pk field ``Item`` declares, by name.

    Walks the model itself, so a field added to ``Item`` is picked up here
    without anyone listing it.
    """
    return {
        field.name
        for field in Item._meta.get_fields()
        if hasattr(field, "attname") and not field.primary_key
    }
