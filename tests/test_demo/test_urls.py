"""Tests for the demo project's URL configuration.

Same subprocess mechanism as ``test_commands.py`` and for the same reason: ``demo`` is deliberately
absent from ``tests.settings`` (plan.md D-10), so the demo's own URLconf can only be exercised from
an interpreter booted on ``demo.settings``.

Nothing here touches the database. ``DEMO_DB_PATH`` still points at ``tmp_path`` because
``demo.settings`` is loaded either way and a stray file next to the developer's real database is
not worth the risk.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# django-mvp's mobile footer menu declares a "home" item with view_name="home"
# (mvp/menus.py:146), and the sidebar and dock render on every page the shell serves.
# A project without a URL of that name logs a reversal failure on every render and
# serves a dead Home button.
URLS_SCRIPT = """
import json
import os

os.environ["DJANGO_SETTINGS_MODULE"] = "demo.settings"
os.environ["DEMO_DB_PATH"] = {db_path!r}

import django
django.setup()

from django.core.management import call_command
from django.test import Client
from django.urls import reverse

# CurrentSiteMiddleware reads django_site on every request, including a redirect that
# renders no template, so even this database-free check needs the schema in place.
call_command("migrate", "--noinput", verbosity=0)

# SERVER_NAME, because django.test.utils.setup_test_environment() — which is what
# normally adds "testserver" to ALLOWED_HOSTS — never runs in a raw subprocess.
# Without it every request here dies with DisallowedHost before reaching a view,
# and a check for "no warning was logged" passes because nothing rendered at all.
response = Client().get("/", SERVER_NAME="127.0.0.1")

print("RESULT_JSON:" + json.dumps({{
    "home": reverse("home"),
    "catalogue": reverse("literature:item-list"),
    "root_status": response.status_code,
    "root_location": response.headers.get("Location"),
}}))
"""


def resolve_urls(db_path: Path) -> dict:
    """Reverse the demo's named routes in a fresh subprocess booted on ``demo.settings``."""
    result = subprocess.run(  # noqa: S603 — fixed interpreter, literal script, no user input
        [sys.executable, "-c", URLS_SCRIPT.format(db_path=str(db_path))],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
    for line in result.stdout.splitlines():
        if line.startswith("RESULT_JSON:"):
            return json.loads(line[len("RESULT_JSON:") :])
    raise AssertionError(f"no RESULT_JSON line in stdout: {result.stdout!r}")


class TestDemoUrls:
    """The demo's URLconf gives the shell everything it reverses (decisions.md D9)."""

    def test_home_reverses_so_the_shell_menus_render_without_error(self, tmp_path):
        urls = resolve_urls(tmp_path / "db.sqlite3")
        assert urls["home"] == "/"

    def test_the_root_sends_a_visitor_to_the_catalogue(self, tmp_path):
        urls = resolve_urls(tmp_path / "db.sqlite3")
        assert urls["root_status"] in (301, 302)
        assert urls["root_location"] == urls["catalogue"]

    def test_no_page_render_logs_a_menu_reversal_failure(self, tmp_path):
        # The regression this file exists for: the warning django-flex-menus emits when
        # it cannot reverse a menu item is written to stderr and does not fail a render,
        # so nothing but an explicit check catches it.
        env = os.environ.copy()
        env["DJANGO_SETTINGS_MODULE"] = "demo.settings"
        env["DEMO_DB_PATH"] = str(tmp_path / "db.sqlite3")

        script = (
            "import django; django.setup();"
            "from django.core.management import call_command;"
            "call_command('migrate', '--noinput', verbosity=0);"
            "from django.test import Client;"
            # SERVER_NAME for the reason given above, and the status assertion because
            # a request that never reached a template logs no menu warning either.
            "response = Client().get('/catalogue/', SERVER_NAME='127.0.0.1');"
            "assert response.status_code == 200, response.status_code"
        )
        result = subprocess.run(  # noqa: S603 — fixed interpreter, literal script, no user input
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=False,
            cwd=REPO_ROOT,
            env=env,
        )

        assert result.returncode == 0, result.stderr
        assert "Could not reverse URL" not in result.stderr
        assert "Reverse error" not in result.stderr
