"""A database on the ``LiteratureItem`` schema, for the upgrade command's tests.

``legacy_database`` swaps the test database's ``literature`` tables and the host
app's table for the schema they had before this package's current models, and
records the old migrations as applied. It yields that schema's models, so a test
creates old rows the way the old package did. Whatever the test leaves behind,
the fixture puts the current schema back, because the database outlives the test.
"""

import pytest
from django.apps import apps
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder
from django.db.migrations.state import ProjectState

from tests.fixtures.legacy_schema import (
    LEGACY_MIGRATIONS,
    LEGACY_OPERATIONS,
    LEGACY_TABLES,
)


def drop_literature_and_host_tables():
    current_tables = [
        model._meta.db_table
        for app_label in ("literature", "host")
        for model in apps.get_app_config(app_label).get_models(
            include_auto_created=True
        )
    ]
    existing = set(connection.introspection.table_names())
    with connection.schema_editor() as editor:
        for table in [*LEGACY_TABLES, *current_tables]:
            if table in existing:
                editor.execute(
                    editor.sql_delete_table % {"table": editor.quote_name(table)}
                )
    MigrationRecorder(connection).migration_qs.filter(
        app__in=["literature", "host"]
    ).delete()


def build_legacy_schema():
    drop_literature_and_host_tables()
    state = ProjectState()
    with connection.schema_editor() as editor:
        for app_label, operation in LEGACY_OPERATIONS:
            new_state = state.clone()
            operation.state_forwards(app_label, new_state)
            operation.database_forwards(app_label, editor, state, new_state)
            state = new_state
    recorder = MigrationRecorder(connection)
    for name in LEGACY_MIGRATIONS:
        recorder.record_applied("literature", name)
    recorder.record_applied("host", "0001_initial")
    return state.apps


def restore_current_schema():
    drop_literature_and_host_tables()
    executor = MigrationExecutor(connection)
    executor.migrate(
        [
            *executor.loader.graph.leaf_nodes("literature"),
            *executor.loader.graph.leaf_nodes("host"),
        ]
    )


@pytest.fixture
def legacy_database(transactional_db):
    with connection.constraint_checks_disabled():
        legacy_apps = build_legacy_schema()
    yield legacy_apps
    with connection.constraint_checks_disabled():
        restore_current_schema()


@pytest.fixture
def legacy_item(legacy_database):
    """Return a function that stores a reference the way the old package did.

    ``item`` is the reference's CSL JSON; its ``type`` and ``title`` are kept on the
    row as well.
    """

    def create(citation_key="pollack1993", **item):
        LiteratureItem = legacy_database.get_model("literature", "LiteratureItem")
        return LiteratureItem.objects.create(
            citation_key=citation_key,
            type=item.get("type", "article-journal"),
            title=item.get("title", ""),
            item=item,
        )

    return create


@pytest.fixture
def legacy_tag(legacy_database):
    """Return a function that stores an old-schema tag."""

    def create(name):
        return legacy_database.get_model("literature", "Tag").objects.create(name=name)

    return create


@pytest.fixture
def legacy_collection(legacy_database):
    """Return a function that stores an old-schema collection."""

    def create(name):
        return legacy_database.get_model("literature", "Collection").objects.create(
            name=name
        )

    return create


@pytest.fixture
def legacy_citation(legacy_database):
    """Return a function that stores a host record citing the old reference ``reference_id``."""

    def create(reference_id):
        return legacy_database.get_model("host", "Citation").objects.create(
            reference_id=reference_id
        )

    return create
