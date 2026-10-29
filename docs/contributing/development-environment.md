# Set up a development environment

Everything you need to change the package, run its tests and serve the demo project lives in the
repository and is installed with [uv](https://docs.astral.sh/uv/).

## Install the tools

You need:

- [Git](https://git-scm.com/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Python 3.12 or later. uv downloads one for you if none is installed.

## Clone the repository

```bash
git clone https://github.com/FAIR-DM/django-literature.git
cd django-literature
```

## Install the dependencies

```bash
uv sync
```

This creates a virtual environment in `.venv` and installs the package with its `ui` extra and the
`dev` dependency group: the test suite's tools, the linters and the type checker. Every command on
these pages runs through `uv run`, so there is nothing to activate.

To build the documentation as well, add the `docs` group:

```bash
uv sync --group docs
```

A later `uv sync` without `--group docs` removes the documentation tools again.

## Install the pre-commit hooks

```bash
uv run pre-commit install
```

The hooks then run on the files of every commit. They are the same checks the pull request's Code
Quality check runs, listed in [Run the tests and checks](tests-and-checks.md).

## Run the demo project

The repository carries a demo project that serves the web interface over a small catalogue of real
references:

```bash
uv run python manage.py migrate
uv run python manage.py seed_demo
uv run python manage.py runserver
```

Open `http://127.0.0.1:8000/catalogue/`. Browsing needs no account. To add, edit, delete or import
references, sign in at `http://127.0.0.1:8000/admin/login/` as `editor.user` with the password
`password`, the account `seed_demo` creates. `demo/seed/import-sample.bib` is there to import.

`seed_demo` clears the catalogue before it loads, so running it again returns the demo to the same
state. Once the database is seeded, `runserver` on its own is enough. The database is
`demo/db.sqlite3`, and the project's settings are in `demo/settings.py`.
