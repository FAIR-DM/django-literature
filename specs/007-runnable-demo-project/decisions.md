# Decisions — 007 A Runnable Demo That Serves the Front End Over Real References

Rationale that would not fit inline in `spec.md`, plus every ambiguity resolved without escalating.
Each decision names what was ambiguous, what was chosen, and why the choice is defensible.

## D1 — The seed catalogue covers a representative range of item types, not all 45
**Ambiguity**: The intake session settled on a curated set on the order of twenty to thirty
references, chosen to "cover the item types the package supports". The store carries 45 CSL item
types (`literature/choices.py`), so the two halves of that sentence cannot both hold literally: a
set of that size cannot carry one of each and still leave room for the contributor, date and
identifier shapes the same session asked for.

**Chosen**: A representative range — the item types a research literature collection actually
contains — rather than one of every type. Exhaustive coverage stays where it already lives.

**Why defensible**: The exhaustive matrix is already a delivered guarantee somewhere better suited
to it. FS-006's SC-008 requires every one of the catalogue's item types to render on both pages,
and the test suite holds that assertion today. Repeating it in the demo would buy no new coverage
while spending the demo's entire budget on a checklist nobody browses, and it would push the
curated set past the point where anyone reviews the data as data. The demo's job is to be looked
at. A catalogue of 45 near-identical stub records is worse at that job than twenty-five real ones
spanning the types a reader recognises, and the intake session asked for the second thing. Where
the two readings conflict, the one that serves the stated purpose wins.

**ADR:** none — the specification states the requirement (FR-010) and the reasoning is local to
this feature.

## D2 — "One command" begins after dependency installation
**Ambiguity**: The issue promises "one documented command" from a standing start. Whether that
command is expected to also install the project's dependencies was not stated, and a Python project
cannot run anything before its environment exists.

**Chosen**: Installing dependencies is a documented precondition. The one-command promise covers
everything after it — database, migrations, seed load, server.

**Why defensible**: A clone of any Python project begins with installing its dependencies, the
repository already documents how, and the environment manager owns that step rather than the
project. Folding it into the demo's command would mean the demo either duplicates instructions that
already exist elsewhere in the repository or takes over environment management for a contributor
who has their own way of doing it. What the issue is actually asking for is that no *undocumented*
or *unsequenced* step stands between a clone and a served page, and that holds: after the install
every project already performs, there is exactly one thing to run and one address to open.

**ADR:** none.

## D3 — The guard asserts on rendered content, not on a status code
**Ambiguity**: "Its pages still render" admits a weak reading — every page returns a success
response — and a strong one.

**Chosen**: Each page must respond successfully *and* carry content from the seed catalogue
(FR-019).

**Why defensible**: The weak reading passes on the exact failure the guard exists to catch. A
catalogue list that finds no items renders perfectly well and returns 200: FS-006's US-1 requires
an empty catalogue to render an empty-state page rather than an error, so an unloaded or
silently-failed seed produces a healthy-looking green check over a demo that shows nothing. The
same holds for a reference page rendering its record with every section empty. Asserting on a
status code alone would leave the guard reporting on Django's ability to return a response, which
nobody doubts, rather than on the demo's ability to show a catalogue, which is the thing that
breaks. This is the general shape of a gate that must be tested against the defect it exists to
catch, which SC-007 makes an explicit obligation rather than an intention.

**ADR:** none.

## D4 — No committed database
**Ambiguity**: A demo project can ship a pre-built database so that starting it is instant, and the
repository currently carries an untracked `demo/db.sqlite3` left over from development.

**Chosen**: The repository holds the reference data as source; the start command builds the
database from it (FR-007). The database file stays out of version control, as it already is.

**Why defensible**: A committed database is a binary that cannot be reviewed, cannot be diffed, and
drifts from the migrations the moment a migration lands without someone remembering to rebuild it —
a drift that would show up as the demo failing to start on a fresh clone while working for everyone
who has the stale file. It also makes the seed catalogue two artifacts that can disagree, and the
guard would then have to choose which one it trusts. Building from source on start costs a few
seconds and removes the whole class of problem. It is also what makes FR-004's promise — that
running the command returns the demo to the seeded state — implementable at all.

**ADR:** none.

## D5 — The demo stays open and creates no account; the admin stays as it is
**Ambiguity**: The demo project mounts Django's admin today. Whether the documented start should
create a superuser, and whether browsing should sit behind a login, was unstated.

**Chosen**: No account is created and no page requires a sign-in (FR-005). The admin mount stays
exactly as it is and is not part of the documented path.

**Why defensible**: FS-006 settled that the front end's pages are open by default, with a host that
wants them protected wiring the include behind its own protection, so a demo that demanded a login
would misrepresent the thing it demonstrates. Creating a superuser would also add a second step to
a one-step promise, or else bake a fixed credential into the repository — a pattern worth avoiding
even in a project explicitly labelled as not production. Leaving the admin mounted costs nothing,
was already true before this feature, and gives anyone who wants to alter the demo's data a way to
do it without the demo advertising it.

**ADR:** none.

## D6 — The guard reports on every pull request rather than filtering by path
**Ambiguity**: The repository's other workflows filter by path on pushes to the default branch. The
natural instinct is to run the demo check only when something the demo depends on changes.

**Chosen**: The check reports on every pull request (FR-022).

**Why defensible**: This is a lesson the repository has already recorded. `tests.yml` carries an
explicit comment on exactly this point: a path-filtered required check never reports on an
out-of-scope pull request, and a required check that never reports blocks the merge outright. The
demo check is intended to be armed as required, so it inherits the same constraint. Beyond the
mechanics, the set of things the demo depends on is wider than it looks — the package, the front
end, the seed data, the dependency lock, the documented install steps — and a path filter is a
list of guesses about that set which goes stale silently. Arming the check as required in the
branch ruleset is the maintainer's action, noted as an assumption rather than delivered here.

**ADR:** none.

## D7 — `seed_demo` reads its catalogue path from `DEMO_SEED_PATH`, mirroring T001's `DEMO_DB_PATH`
**Ambiguity**: tasks.md T006 requires a test proving that running `seed_demo` "against a catalogue
holding different items leaves only the seeded ones" — i.e. the test must run the command twice
against two different catalogue contents. `seed_demo` (T008) always loads a fixed file,
`demo/seed/catalogue.json`. Overwriting that tracked file from a test, even temporarily, mutates a
repository file mid-run with no safe rollback if the test aborts, and neither `tasks.md` nor
`plan.md` names a parameter for the catalogue path.

**Chosen**: `seed_demo` reads its catalogue path from the `DEMO_SEED_PATH` environment variable,
defaulting to `demo/seed/catalogue.json` — the same shape T001 already established for
`DEMO_DB_PATH`, for the identical reason: a destructive command needs a way for a test to point it
at a scratch file instead of the tracked one. With no variable set, `python manage.py seed_demo`
and `python manage.py demo` behave exactly as if the path were hardcoded.

**Why defensible**: This is a narrower instance of the exact problem T001 already solved for the
database file, solved the same way, so it introduces no new pattern. It touches only
`demo/management/commands/seed_demo.py` (T008's own file) and costs the production path nothing —
the default is unchanged. The alternative (mutating and restoring `demo/seed/catalogue.json` inside
the test) was rejected because a test that dies mid-run would leave the tracked seed file
corrupted, which is worse than one extra environment variable.

**Revisit if**: a later story gives `seed_demo` a `--file` CLI argument for a different reason: at
that point `DEMO_SEED_PATH` should be folded into it rather than the project carrying both.

**ADR**: none.

## D8 — The missing-'ui'-extra guard lives in `demo/settings.py`, not in `demo.py`
**Ambiguity**: T009 asks `python manage.py demo` to "fail with a plain message naming the missing
extra when literature.ui is not installed, rather than dying inside Django's app loading," and
names `demo/management/commands/demo.py` as the file to write.

**Chosen**: The guard is a `try/except ImportError` around `import mvp` at the top of
`demo/settings.py`, printing a one-line message and calling `sys.exit(1)` — not code inside
`demo.py`'s `handle()`.

**Why defensible**: `django.core.management.ManagementUtility.execute()` calls `django.setup()` —
which imports every `INSTALLED_APPS` entry, including `mvp`, `django_cotton`, `easy_icons`,
`flex_menu`, `crispy_forms` and `crispy_tailwind` — unconditionally, before `fetch_command()` even
locates and imports `demo.py`. I read the installed Django 5.2 source
(`django/core/management/__init__.py:353-417`) to confirm this ordering. A missing dependency
therefore crashes before any code in `demo.py` runs; nothing written there can intercept it. The
only point early enough is settings-module load, which `execute()` reaches (via
`settings.INSTALLED_APPS`) before calling `django.setup()`. `mvp` is the canary because it is the
first `ui`-only package the front end genuinely needs (README.md) and is a hard dependency of every
other one; catching it there is the earliest point at which a plain, one-line message can be shown
instead of a raw `ModuleNotFoundError` traceback surfacing from deep inside app loading. This
guard applies to every management command, not just `demo` — which is correct given T001 already
requires the `ui` apps to be unconditional in `INSTALLED_APPS`: no command works without them.

**Revisit if**: `demo/settings.py` ever needs to run without the `ui` extra for a legitimate reason
(e.g. a future core-only demo mode) — at that point the apps and the guard both need to become
conditional together, not just the guard.

**ADR**: none.
