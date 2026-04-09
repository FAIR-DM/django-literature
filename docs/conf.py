# Configuration file for the Sphinx documentation builder.
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

# Make the project root importable so autodoc can find the `literature` package.
sys.path.insert(0, os.path.abspath(".."))

# Configure Django so that autodoc can import Django models without raising
# ``django.core.exceptions.ImproperlyConfigured``.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

import django  # noqa: E402

django.setup()

# ---------------------------------------------------------------------------
# Project information
# ---------------------------------------------------------------------------

project = "django-literature"
copyright = "2024, Sam Jennings"
author = "Sam Jennings"
release = "0.1.0"

# ---------------------------------------------------------------------------
# General configuration
# ---------------------------------------------------------------------------

extensions = [
    # First-party Sphinx extensions
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",  # NumPy / Google-style docstrings
    # Third-party extensions (installed via fairdm-docs)
    "myst_parser",           # Parse Markdown source files
    "sphinx_design",         # Cards, grids, tabs
    "sphinx_copybutton",     # Copy-button on code blocks
]

# Markdown file support
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "myst",
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# ---------------------------------------------------------------------------
# MyST-Parser options
# ---------------------------------------------------------------------------

myst_enable_extensions = [
    "colon_fence",      # ::: fences (like GitHub Callouts)
    "deflist",          # Definition lists
    "tasklist",         # - [ ] task items
]

# ---------------------------------------------------------------------------
# HTML output
# ---------------------------------------------------------------------------

html_theme = "alabaster"

html_theme_options = {
    "description": "Bibliographic reference management for Django, built on CSL JSON.",
    "github_user": "SSJenny90",
    "github_repo": "django-literature",
    "github_banner": True,
    "github_button": True,
    "fixed_sidebar": True,
}

html_static_path = ["_static"]

# ---------------------------------------------------------------------------
# autodoc options
# ---------------------------------------------------------------------------

autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
}

# Do not skip __init__ — some models have meaningful __init__ behaviour.
autodoc_class_signature = "mixed"

# ---------------------------------------------------------------------------
# intersphinx — link to upstream docs
# ---------------------------------------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "django": ("https://docs.djangoproject.com/en/stable/", "https://docs.djangoproject.com/en/stable/_objects/"),
}

# ---------------------------------------------------------------------------
# Napoleon — docstring style
# ---------------------------------------------------------------------------

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = False
