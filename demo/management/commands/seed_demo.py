"""``python manage.py seed_demo`` — reload the demo catalogue from its seed file (FS-007)."""

import json
import os
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from literature.converters import from_csl_json_list
from literature.models import Item, Name

DEFAULT_SEED_PATH = (
    Path(__file__).resolve().parent.parent.parent / "seed" / "catalogue.json"
)


#: The demo's one account: holds every write permission, and ``is_staff`` lets it sign in
#: through the admin's login page, the demo's only one.
EDITOR_USERNAME = "editor.user"
EDITOR_PASSWORD = "password"  # noqa: S105 — a published demo login, not a secret
EDITOR_PERMISSIONS = ("add_item", "change_item", "delete_item")


def seed_editor():
    """Create the demo's editor, or reset an existing one to its known password."""
    editor, _created = get_user_model().objects.get_or_create(
        username=EDITOR_USERNAME, defaults={"is_staff": True}
    )
    editor.is_staff = True
    editor.set_password(EDITOR_PASSWORD)
    editor.save()
    editor.user_permissions.set(
        Permission.objects.filter(
            content_type__app_label="literature", codename__in=EDITOR_PERMISSIONS
        )
    )


def key_of(entry):
    """Return the citation key a loaded Item would carry, as the converter reads it.

    Args:
        entry: A CSL JSON item dict.

    Returns:
        ``citation-key``, falling back to ``id``.
    """
    return entry.get("citation-key") or entry.get("id")


class Command(BaseCommand):
    """Delete every ``Item`` and ``Name``, reload the demo catalogue, and seed the editor.

    Destructive: anything entered through the admin is lost.
    """

    help = (
        "Delete every Item and every Name, then reload the demo catalogue from "
        "demo/seed/catalogue.json. Destructive: anything entered through the admin is lost."
    )

    def handle(self, *args, **options):
        """Run the delete-and-reload as one operation."""
        # Atomic so a partial load, which only the count check below notices, rolls back
        # the delete and leaves the previous catalogue in place.
        with transaction.atomic():
            # Name is not reachable from Item's cascade; deleting Item alone would leave
            # every loaded contributor behind (FS-007).
            Item.objects.all().delete()
            Name.objects.all().delete()

            seed_path = Path(os.environ.get("DEMO_SEED_PATH", str(DEFAULT_SEED_PATH)))
            # JSON is UTF-8 (RFC 8259 §8.1); the locale's encoding would turn "Gödel" into
            # mojibake on a cp1252 machine.
            with seed_path.open(encoding="utf-8") as f:
                entries = json.load(f)

            loaded = from_csl_json_list(entries)

            if len(loaded) != len(entries):
                # from_csl_json_list skips invalid entries rather than raising (FS-007).
                loaded_keys = {item.citation_key for item in loaded}
                missing = [
                    key_of(entry) or "<unidentified entry>"
                    for entry in entries
                    if key_of(entry) not in loaded_keys
                ]
                raise CommandError(
                    f"seed_demo loaded {len(loaded)} of {len(entries)} entries from {seed_path}; "
                    f"failed to load: {', '.join(missing)}"
                )

            seed_editor()

        self.stdout.write(
            self.style.SUCCESS(
                f"seed_demo loaded {len(loaded)} references from {seed_path}, "
                f"and {EDITOR_USERNAME} can sign in with the password {EDITOR_PASSWORD!r}"
            )
        )
