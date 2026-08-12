"""``python manage.py seed_demo`` — plan.md D-2."""

import json
import os
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from literature.converters import from_csl_json_list
from literature.models import Item, Name

_DEFAULT_SEED_PATH = Path(__file__).resolve().parent.parent.parent / "seed" / "catalogue.json"


def _key_of(entry):
    """The citation key a loaded Item would carry, as the converter reads it."""
    return entry.get("citation-key") or entry.get("id")


class Command(BaseCommand):
    help = (
        "Delete every Item and every Name, then reload the demo catalogue from "
        "demo/seed/catalogue.json. Destructive: anything entered through the admin is lost."
    )

    def handle(self, *args, **options):
        # The delete and the load are one operation. The converter skips an invalid
        # entry rather than raising, so the count check below is the only thing that
        # notices a partial load — and by then the previous catalogue is already
        # deleted. Without this, the failure the command exists to report would leave
        # the database at neither the old state nor the new one (RC-002).
        with transaction.atomic():
            # Name is shared between items and is not reachable from Item's cascade, and
            # the converter reuses rows with get_or_create — deleting Item alone would
            # leave every contributor ever loaded behind (plan.md D-2).
            Item.objects.all().delete()
            Name.objects.all().delete()

            seed_path = Path(os.environ.get("DEMO_SEED_PATH", str(_DEFAULT_SEED_PATH)))
            # encoding="utf-8" is not optional here. Without it Python uses the
            # locale's preferred encoding, so the same file loads differently on
            # different machines: the catalogue holds a German thesis title, Gödel
            # and Françoise Sagan, and on a cp1252 locale every one of those arrives
            # as mojibake ("GÃ¶del") and is stored that way. JSON is UTF-8 by
            # specification (RFC 8259 §8.1), so the file's encoding is a fact about
            # the format rather than a property of whoever opens it.
            with seed_path.open(encoding="utf-8") as f:
                entries = json.load(f)

            loaded = from_csl_json_list(entries)

            if len(loaded) != len(entries):
                # from_csl_json_list skips an invalid entry with a warning rather than
                # raising, so a half-loaded catalogue must be caught here (FR-020).
                loaded_keys = {item.citation_key for item in loaded}
                missing = [
                    _key_of(entry) or "<unidentified entry>" for entry in entries if _key_of(entry) not in loaded_keys
                ]
                raise CommandError(
                    f"seed_demo loaded {len(loaded)} of {len(entries)} entries from {seed_path}; "
                    f"failed to load: {', '.join(missing)}"
                )

        self.stdout.write(self.style.SUCCESS(f"seed_demo loaded {len(loaded)} references from {seed_path}"))
