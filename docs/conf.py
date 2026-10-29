"""Sphinx settings for the package's documentation.

The site is built on fairdm-docs, which reads the project's name, version, authors and
repository from pyproject.toml and supplies the theme chosen there, the extensions and MyST options. This
file adds only what the package's own pages need: Django set up so autodoc can import
the models, and autodoc itself for the API reference.
"""

import os
import sys

import django

# Make the project root importable so autodoc can find the `literature` package, with
# the test settings, which install every app the package's modules import.
sys.path.insert(0, os.path.abspath(".."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
django.setup()

from fairdm_docs.conf import *  # noqa: E402, F403

extensions.append("sphinx.ext.autodoc")  # noqa: F405

# docs/agents/ configures tooling for automated contributors and is not part of the site.
exclude_patterns.append("agents")  # noqa: F405

# The package ships no static files of its own, and the logo and icon come from
# fairdm-docs.
html_static_path: list[str] = []

# The site's name as a reader writes it. fairdm-docs takes the distribution name from
# pyproject.toml, which is the name to install, not the name to show.
project = "Django Literature"
html_title = project

# Every section of the site sits in the navbar, Home first.
html_theme_options["header_links_before_dropdown"] = 6  # noqa: F405

# A ``type[BibFormat]`` annotation names the builtin ``type``, which Sphinx also matches
# against the ``type`` fields of ``Item`` and ``ItemIdentifier`` and reports as ambiguous.
# The builtin is what every such annotation means, so the warning carries nothing to fix.
# MyST warns on every strikethrough that it renders only in HTML, which is the only
# output this site is built as. Superseded decision records use it.
suppress_warnings = ["ref.python", "myst.strikethrough", "autosectionlabel.release-notes"]

autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
}
autodoc_class_signature = "mixed"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "django": (
        "https://docs.djangoproject.com/en/stable/",
        "https://docs.djangoproject.com/en/stable/_objects/",
    ),
}

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = False
# Dataclass fields are already documented by autodoc. Rendering an Attributes: section
# as :ivar: fields keeps them from being declared twice.
napoleon_use_ivar = True

# Section links such as installation.md#install-the-front-end resolve to headings.
myst_heading_anchors = 3
