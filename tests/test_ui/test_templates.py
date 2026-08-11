"""Tests for the templates ``literature.ui`` ships."""

from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "literature" / "ui" / "templates" / "literature" / "ui"

# django-mvp's own packaged chain (research R2, plan.md D-1) — the app must
# never reach any of these, since a host that has not written its own
# base.html would get TemplateDoesNotExist through the packaged chain, and a
# top-level base.html of our own would hijack the host's shell.
FORBIDDEN_REFERENCES = ["page_view.html", "list_view.html", "detail_view.html"]


class TestBaseTemplate:
    """``literature/ui/templates/literature/ui/base.html`` — plan.md D-1."""

    @staticmethod
    def _source() -> str:
        return (TEMPLATES_DIR / "base.html").read_text()

    def test_extends_mvp_base_directly(self):
        assert '{% extends "mvp/base.html" %}' in self._source()

    def test_references_none_of_the_packaged_view_chain(self):
        source = self._source()
        for forbidden in FORBIDDEN_REFERENCES:
            assert forbidden not in source

    def test_does_not_extend_or_include_the_unqualified_base_template(self):
        source = self._source()
        assert '"base.html"' not in source
        assert "'base.html'" not in source

    def test_renders_the_page_wrapper_class(self):
        assert '<c-page class="{{ page.class }}">' in self._source()

    def test_renders_the_breadcrumbs_region(self):
        assert "<c-breadcrumbs" in self._source()
