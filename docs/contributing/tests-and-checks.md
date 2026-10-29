# Run the tests and checks

A pull request has to pass the test suite, the code checks and the demo walk, and the documentation
has to build. Each runs locally with the commands below, the same ones the repository's checks run.
Install the dependencies first, as [Set up a development environment](development-environment.md)
describes.

## Run the test suite

```bash
uv run pytest
```

The suite runs with the test settings in `tests/settings.py` and measures the coverage of the
`literature` package as it goes. The coverage report is written to `htmlcov/index.html`. The pull
request runs the suite on Python 3.12 and 3.13 against Django 5.2, 6.0 and 6.1.

## Run the code checks

```bash
uv run pre-commit run --all-files
```

These are the hooks the pull request's Code Quality check runs:

- trailing whitespace, a newline at the end of every file, and valid YAML
- `uv.lock` up to date with `pyproject.toml`
- [Ruff](https://docs.astral.sh/ruff/) linting and formatting
- [mypy](https://mypy.readthedocs.io/) over `literature/`
- [deptry](https://deptry.com/), which checks that every import is a declared dependency

The hooks that fix what they find, such as the formatter, rewrite the files and report a failure.
Run the command again to confirm the rest pass.

## Walk the demo

The pull request starts the demo project and follows its pages from the catalogue, adding, editing,
importing and deleting references as it goes. With the demo running, as in
[Run the demo project](development-environment.md#run-the-demo-project), run the same walk from a
second terminal:

```bash
uv run python demo/smoke.py http://127.0.0.1:8000
```

The walk changes the catalogue. Run `uv run python manage.py seed_demo` afterwards to return it to
its seeded state.

## Build the documentation

```bash
uv sync --group docs
uv run sphinx-build -E -W -b html docs docs/_build
```

This is the build that publishes the site once a change reaches `main`, with `-W` added so a warning
stops it. The site builds without warnings, and a change should keep it that way. Open
`docs/_build/index.html` to read the result.

To preview the site while you write, serve it with a rebuild on every change:

```bash
uv run fairdm-docs build --live
```
