"""``python manage.py demo`` — plan.md D-2, the one documented command (FR-003)."""

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Migrate, seed and serve the demo: the one command a fresh clone needs."

    def handle(self, *args, **options):
        call_command("migrate", verbosity=1)
        call_command("seed_demo")
        self.stdout.write(self.style.SUCCESS("Open http://127.0.0.1:8000/catalogue/ to browse the demo."))
        # The autoreloader relaunches "manage.py demo" verbatim in a child process,
        # so leaving it on re-runs the destructive seed at every start and on every
        # file save (plan.md D-2).
        call_command("runserver", use_reloader=False)
