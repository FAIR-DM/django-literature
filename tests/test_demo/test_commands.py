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
import os
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_REAL_CATALOGUE = _REPO_ROOT / "demo" / "seed" / "catalogue.json"
_MANAGE_PY = _REPO_ROOT / "manage.py"

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

# Reads the database without writing to it, so a test can state what a *failed*
# seed_demo left behind. Runs no migration: the database it inspects has already
# been migrated by the seed run under test.
_INSPECT_SCRIPT = """
import json
import os

os.environ["DJANGO_SETTINGS_MODULE"] = "demo.settings"
os.environ["DEMO_DB_PATH"] = {db_path!r}

import django
django.setup()

from literature.models import Item

print("RESULT_JSON:" + json.dumps({{
    "item_count": Item.objects.count(),
    "citation_keys": sorted(Item.objects.values_list("citation_key", flat=True)),
}}))
"""


def _read_result_json(result: subprocess.CompletedProcess) -> dict:
    for line in result.stdout.splitlines():
        if line.startswith("RESULT_JSON:"):
            return json.loads(line[len("RESULT_JSON:") :])
    raise AssertionError(f"no RESULT_JSON line in stdout: {result.stdout!r}")


def _inspect(db_path: Path) -> dict:
    """What ``db_path`` holds now, read in a fresh subprocess."""
    result = subprocess.run(  # noqa: S603 — fixed interpreter, literal script, no user input
        [sys.executable, "-c", _INSPECT_SCRIPT.format(db_path=str(db_path))],
        capture_output=True,
        text=True,
        check=False,
        cwd=_REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
    return _read_result_json(result)


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
    return _read_result_json(result)


def _run_seed_demo_strict_encoding(db_path: Path, seed_path: Path) -> subprocess.CompletedProcess:
    """Run ``seed_demo`` with every implicit text encoding escalated to an error.

    ``-X warn_default_encoding`` makes CPython emit an ``EncodingWarning`` wherever
    text I/O falls back to ``locale.getpreferredencoding()``, and turning that
    warning into an error is what makes the check independent of the locale the
    suite happens to run under. Asserting the titles come back correct would not
    work: on a UTF-8 machine they do so whether or not the encoding was named.
    """
    script = _SEED_DEMO_SCRIPT.format(db_path=str(db_path), seed_path=str(seed_path))
    env = os.environ.copy()
    env["PYTHONWARNINGS"] = "error::EncodingWarning"
    return subprocess.run(  # noqa: S603 — fixed interpreter, literal script, no user input
        [sys.executable, "-X", "warn_default_encoding", "-c", script],
        capture_output=True,
        text=True,
        check=False,
        cwd=_REPO_ROOT,
        env=env,
    )


class TestSeedDemo:
    """``python manage.py seed_demo`` — plan.md D-2."""

    def test_loads_the_catalogue(self, tmp_path):
        result = _run_seed_demo(tmp_path / "db.sqlite3", _REAL_CATALOGUE)
        catalogue = json.loads(_REAL_CATALOGUE.read_text(encoding="utf-8"))
        assert result["item_count"] == len(catalogue)
        assert result["item_count"] > 0

    def test_names_every_text_encoding_it_opens_a_file_with(self, tmp_path):
        # The catalogue holds Gödel, a German thesis title and Françoise Sagan. An
        # open() that does not name its encoding uses the locale's, so on a cp1252
        # machine every one of those loads as mojibake ("GÃ¶del") and is stored that
        # way — while the same command on a UTF-8 machine, and in CI, is perfectly
        # fine. Escalating EncodingWarning to an error catches the whole class here
        # rather than leaving it to whoever runs the demo on a different locale.
        result = _run_seed_demo_strict_encoding(tmp_path / "db.sqlite3", _REAL_CATALOGUE)
        assert result.returncode == 0, f"implicit text encoding on the seed path:\n{result.stderr}"

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

    def test_a_failed_seed_leaves_the_catalogue_exactly_as_it_was(self, tmp_path):
        # The command deletes before it loads, so without a transaction the
        # partial-load failure it is built to detect (FR-020) would report
        # correctly and still leave the database holding neither the previous
        # catalogue nor the new one (RC-002).
        db_path = tmp_path / "db.sqlite3"
        good = tmp_path / "good.json"
        good.write_text(json.dumps([{"citation-key": "Alpha2020", "type": "book", "title": "Alpha"}]))
        partial = tmp_path / "partial.json"
        partial.write_text(
            json.dumps(
                [
                    {"citation-key": "Beta2021", "type": "book", "title": "Beta"},
                    {"citation-key": "Bad2020", "type": "not-a-real-type", "title": "Bad"},
                ]
            )
        )

        _run_seed_demo(db_path, good)
        result = _run_seed_demo_raw(db_path, partial)

        assert result.returncode != 0
        assert _inspect(db_path)["citation_keys"] == ["Alpha2020"]


class TestMissingUIExtra:
    """The demo says so plainly when the ``ui`` extra was never installed.

    The subject is the import guard in ``demo/settings.py``, so this holds for every
    step of the documented sequence rather than for one composite command. It is
    checked against ``migrate``, the first step someone runs (decisions.md D14).
    """

    def test_fails_with_a_plain_message_when_the_ui_extra_is_missing(self, tmp_path):
        # django.setup() populates every INSTALLED_APPS entry before any management
        # command's handle() runs (django.core.management.ManagementUtility.execute()),
        # so a missing UI dependency can only be caught before that point — in
        # demo/settings.py itself (decisions.md D8). Shadow the real "mvp" package
        # with a stub that fails to import, to simulate the ui extra never having
        # been installed.
        stub_dir = tmp_path / "stub"
        stub_dir.mkdir()
        (stub_dir / "mvp.py").write_text("raise ImportError(\"No module named 'mvp'\")\n")

        env = os.environ.copy()
        env["DJANGO_SETTINGS_MODULE"] = "demo.settings"
        env["DEMO_DB_PATH"] = str(tmp_path / "db.sqlite3")
        env["PYTHONPATH"] = str(stub_dir) + os.pathsep + env.get("PYTHONPATH", "")

        result = subprocess.run(  # noqa: S603 — fixed interpreter, literal args, no user input
            [sys.executable, str(_MANAGE_PY), "migrate"],
            capture_output=True,
            text=True,
            check=False,
            cwd=_REPO_ROOT,
            env=env,
        )

        assert result.returncode != 0
        assert "Traceback" not in result.stderr
        assert "ui" in result.stderr.lower()
        assert "pip install django-literature[ui]" in result.stderr
