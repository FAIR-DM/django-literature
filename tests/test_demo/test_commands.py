"""Tests for the demo project's management commands.

``demo`` is deliberately absent from ``tests.settings.INSTALLED_APPS`` (plan.md D-10) — adding it
there would put the demo's app registry inside the suite's wiring, the exact coupling FR-021
forbids. So each test here runs the command under test in a fresh subprocess booted from
``demo.settings``, following the mechanism ``tests/test_ui/test_smoke.py`` already established:
``django.setup()`` runs once per interpreter and the pytest session has already populated the app
registry from ``tests.settings``.

``DEMO_DB_PATH`` (T001) points the subprocess at ``tmp_path`` instead of the developer's real demo
database — ``pytest-django``'s test-database isolation does not reach a subprocess, so without this
the suite would delete the developer's own demo data. ``DEMO_SEED_PATH`` (this task) gives each test
control over which catalogue file ``seed_demo`` loads, so the "different items" scenario never has
to overwrite the tracked ``demo/seed/catalogue.json``.
"""

import json
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_REAL_CATALOGUE = _REPO_ROOT / "demo" / "seed" / "catalogue.json"

# Force, not setdefault: pytest-django exports DJANGO_SETTINGS_MODULE=tests.settings
# into the environment, and this subprocess inherits it by default.
_SEED_DEMO_SCRIPT = """
import json
import os

os.environ["DJANGO_SETTINGS_MODULE"] = "demo.settings"
os.environ["DEMO_DB_PATH"] = {db_path!r}
os.environ["DEMO_SEED_PATH"] = {seed_path!r}

import django
django.setup()

from django.core.management import call_command

call_command("migrate", "--noinput", verbosity=0)
call_command("seed_demo", verbosity=0)

from literature.models import Item, Name

print("RESULT_JSON:" + json.dumps({{
    "item_count": Item.objects.count(),
    "name_count": Name.objects.count(),
    "citation_keys": sorted(Item.objects.values_list("citation_key", flat=True)),
}}))
"""


def _run_seed_demo_raw(db_path: Path, seed_path: Path) -> subprocess.CompletedProcess:
    """Run ``seed_demo`` in a fresh subprocess, returning the raw completed process."""
    script = _SEED_DEMO_SCRIPT.format(db_path=str(db_path), seed_path=str(seed_path))
    return subprocess.run(  # noqa: S603 — fixed interpreter, literal script, no user input
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
        cwd=_REPO_ROOT,
    )


def _run_seed_demo(db_path: Path, seed_path: Path) -> dict:
    """Run ``seed_demo`` in a fresh subprocess against ``db_path``, seeded from ``seed_path``."""
    result = _run_seed_demo_raw(db_path, seed_path)
    assert result.returncode == 0, result.stderr
    for line in result.stdout.splitlines():
        if line.startswith("RESULT_JSON:"):
            return json.loads(line[len("RESULT_JSON:") :])
    raise AssertionError(f"no RESULT_JSON line in stdout: {result.stdout!r}")


class TestSeedDemo:
    """``python manage.py seed_demo`` — plan.md D-2."""

    def test_loads_the_catalogue(self, tmp_path):
        result = _run_seed_demo(tmp_path / "db.sqlite3", _REAL_CATALOGUE)
        catalogue = json.loads(_REAL_CATALOGUE.read_text())
        assert result["item_count"] == len(catalogue)
        assert result["item_count"] > 0

    def test_running_twice_leaves_the_same_number_not_double(self, tmp_path):
        db_path = tmp_path / "db.sqlite3"
        first = _run_seed_demo(db_path, _REAL_CATALOGUE)
        second = _run_seed_demo(db_path, _REAL_CATALOGUE)
        assert second["item_count"] == first["item_count"]

    def test_reseeding_with_different_items_leaves_only_the_new_ones(self, tmp_path):
        db_path = tmp_path / "db.sqlite3"
        catalogue_a = tmp_path / "catalogue_a.json"
        catalogue_a.write_text(
            json.dumps(
                [
                    {"citation-key": "Alpha2020", "type": "article-journal", "title": "Alpha"},
                ]
            )
        )
        catalogue_b = tmp_path / "catalogue_b.json"
        catalogue_b.write_text(
            json.dumps(
                [
                    {"citation-key": "Beta2021", "type": "book", "title": "Beta"},
                    {"citation-key": "Gamma2022", "type": "book", "title": "Gamma"},
                ]
            )
        )

        _run_seed_demo(db_path, catalogue_a)
        result = _run_seed_demo(db_path, catalogue_b)

        assert result["item_count"] == 2
        assert result["citation_keys"] == ["Beta2021", "Gamma2022"]

    def test_fails_non_zero_and_names_entries_when_fewer_load_than_the_file_holds(self, tmp_path):
        db_path = tmp_path / "db.sqlite3"
        catalogue = tmp_path / "catalogue.json"
        catalogue.write_text(
            json.dumps(
                [
                    {"citation-key": "Good2020", "type": "book", "title": "Good"},
                    # "not-a-real-type" is not a recognised CSL JSON item type, so
                    # from_csl_json_list skips this entry and logs a warning
                    # (literature/converters.py) — seed_demo must not report success.
                    {"citation-key": "Bad2020", "type": "not-a-real-type", "title": "Bad"},
                ]
            )
        )

        result = _run_seed_demo_raw(db_path, catalogue)

        assert result.returncode != 0
        assert "Bad2020" in result.stderr
        assert "1" in result.stderr and "2" in result.stderr
