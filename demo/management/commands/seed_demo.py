"""``python manage.py seed_demo`` — plan.md D-2."""

import json
import os
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from literature.converters import from_csl_json_list
from literature.models import Item, Name

_DEFAULT_SEED_PATH = Path(__file__).resolve().parent.parent.parent / "seed" / "catalogue.json"


class Command(BaseCommand):
    help = (
        "Delete every Item and every Name, then reload the demo catalogue from "
        "demo/seed/catalogue.json. Destructive: anything entered through the admin is lost."
    )

    def handle(self, *args, **options):
        # Name is shared between items and is not reachable from Item's cascade, and
        # the converter reuses rows with get_or_create — deleting Item alone would
        # leave every contributor ever loaded behind (plan.md D-2).
        Item.objects.all().delete()
        Name.objects.all().delete()

        seed_path = Path(os.environ.get("DEMO_SEED_PATH", str(_DEFAULT_SEED_PATH)))
        with seed_path.open() as f:
            entries = json.load(f)

        loaded = from_csl_json_list(entries)

        if len(loaded) != len(entries):
            # from_csl_json_list skips an invalid entry with a warning rather than
            # raising, so a half-loaded catalogue must be caught here (FR-020).
            loaded_keys = {item.citation_key for item in loaded}
            missing = [
                entry.get("citation-key") or entry.get("id") or "<unidentified entry>"
                for entry in entries
                if (entry.get("citation-key") or entry.get("id")) not in loaded_keys
            ]
            raise CommandError(
                f"seed_demo loaded {len(loaded)} of {len(entries)} entries from {seed_path}; "
                f"failed to load: {', '.join(missing)}"
            )

        self.stdout.write(self.style.SUCCESS(f"seed_demo loaded {len(loaded)} references from {seed_path}"))
