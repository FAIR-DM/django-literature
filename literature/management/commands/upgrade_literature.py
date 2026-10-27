"""Move a database from the ``LiteratureItem`` schema to the current models."""

import copy
import json
import re

from django.apps import apps
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import no_style
from django.db import DEFAULT_DB_ALIAS, connections, router, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder
from django.db.migrations.state import ProjectState

from literature.converters import from_csl_json
from literature.models import Item

#: The last migration of the ``LiteratureItem`` schema. A database that records
#: it as applied is on that schema.
LEGACY_LAST_MIGRATION = "0004_alter_literatureitem_options"

#: The ``LiteratureItem`` schema's tables, link tables first.
LEGACY_TABLES = (
    "literature_literatureitem_keyword",
    "literature_literatureitem_collections",
    "literature_supplementarymaterial",
    "literature_literatureitem",
    "literature_tag",
    "literature_collection",
)


class Command(BaseCommand):
    """Upgrade a database from the ``LiteratureItem`` schema to the current models.

    Before its current models, ``literature`` shipped a different schema under the
    same app label, with migrations ``0001_initial`` to
    ``0004_alter_literatureitem_options``. Two of those names are reused by the
    current history, so ``migrate`` fails on a database on the old schema. This
    command builds the current tables, converts every ``LiteratureItem`` from the
    CSL JSON it stored, keeping its primary key, and points the host project's
    foreign keys at the new table. See ``docs/how-to/upgrading-from-literatureitem.md``.
    """

    help = (
        "Move a database from the LiteratureItem schema to the current models, "
        "keeping every reference and its primary key. Run it before migrate."
    )

    def add_arguments(self, parser):
        """Add ``--database`` and ``--discard-unconverted``."""
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            help="The database holding the literature tables. Defaults to 'default'.",
        )
        parser.add_argument(
            "--discard-unconverted",
            action="store_true",
            help=(
                "Upgrade even though some references belong to collections, have "
                "supplementary material or have a file attached. The current models "
                "have no place for these, so they are dropped. Files stay in storage."
            ),
        )

    def handle(self, *args, database, discard_unconverted, **options):
        """Run the upgrade in one transaction, or change nothing."""
        connection = connections[database]
        recorder = MigrationRecorder(connection)
        if ("literature", LEGACY_LAST_MIGRATION) not in recorder.applied_migrations():
            self.stdout.write(
                "Nothing to upgrade: the database is not on the old schema."
            )
            return

        with connection.cursor() as cursor:
            references = self.read_references(cursor)
            unconverted = self.read_unconverted(cursor)
        if unconverted and not discard_unconverted:
            raise CommandError(
                "These references belong to collections, have supplementary material "
                "or have a file attached, which the current models have no place for: "
                f"{', '.join(sorted(unconverted))}. Nothing was changed. Run again with "
                "--discard-unconverted to upgrade without them."
            )

        with (
            connection.constraint_checks_disabled(),
            transaction.atomic(using=database),
        ):
            recorder.migration_qs.filter(app="literature").delete()
            executor = MigrationExecutor(connection)
            # Start from an empty state: the default would load the host's migrations, whose
            # foreign keys to Item cannot resolve while literature's are unapplied.
            executor.migrate(
                executor.loader.graph.leaf_nodes("literature"), state=ProjectState()
            )

            failures = self.convert(references, database)
            if failures:
                raise CommandError(
                    "These references could not be converted, so nothing was changed:\n"
                    + "\n".join(failures)
                )
            with connection.cursor() as cursor:
                self.carry_timestamps(cursor)
                for sql in connection.ops.sequence_reset_sql(no_style(), [Item]):
                    cursor.execute(sql)
            with connection.schema_editor() as editor:
                repointed = self.repoint_foreign_keys(editor, database)
                for table in LEGACY_TABLES:
                    editor.execute(
                        editor.sql_delete_table % {"table": editor.quote_name(table)}
                    )

        self.stdout.write(f"Upgraded {len(references)} references.")
        for label in repointed:
            self.stdout.write(f"Pointed {label} at the current reference table.")
        if unconverted:
            self.stdout.write(
                f"Discarded collections, supplementary material and files of "
                f"{len(unconverted)} references."
            )

    def read_references(self, cursor):
        """Return each old reference as ``(pk, CSL JSON)``, its tags among its keywords.

        The row's own citation key and type win over the stored JSON's, because
        the old package kept the row's values authoritative.

        Args:
            cursor: A cursor on the database holding the old tables.

        Returns:
            A list of ``(primary key, CSL JSON dict)`` pairs, in primary key order.
        """
        cursor.execute(
            "SELECT k.literatureitem_id, t.name FROM literature_literatureitem_keyword k"
            " JOIN literature_tag t ON t.id = k.tag_id ORDER BY k.id"
        )
        tags = {}
        for pk, name in cursor.fetchall():
            tags.setdefault(pk, []).append(name)

        cursor.execute(
            "SELECT id, citation_key, type, item FROM literature_literatureitem"
            " ORDER BY id"
        )
        references = []
        for pk, citation_key, item_type, item in cursor.fetchall():
            data = json.loads(item) if isinstance(item, str) else dict(item)
            data["citation-key"] = citation_key
            data.setdefault("type", item_type)
            if pk in tags:
                data["keyword"] = self.merge_keywords(data.get("keyword"), tags[pk])
            references.append((pk, data))
        return references

    def merge_keywords(self, keyword, tags):
        """Return the stored keyword string with every tag not already in it appended.

        Args:
            keyword: The JSON's ``keyword`` value, if it held one.
            tags: The names of the reference's tags, in the order they were added.

        Returns:
            The keywords as one comma-separated string.
        """
        keywords = []
        if isinstance(keyword, str):
            keywords = [
                part.strip() for part in re.split(r"[,;]", keyword) if part.strip()
            ]
        keywords += [tag for tag in tags if tag not in keywords]
        return ", ".join(keywords)

    def read_unconverted(self, cursor):
        """Return the citation keys of references holding what the current models cannot.

        Args:
            cursor: A cursor on the database holding the old tables.

        Returns:
            The citation keys of references in a collection, with supplementary
            material, or with a file attached.
        """
        cursor.execute(
            "SELECT citation_key FROM literature_literatureitem WHERE"
            " (file IS NOT NULL AND file <> '')"
            " OR id IN (SELECT literatureitem_id FROM literature_literatureitem_collections)"
            " OR id IN (SELECT literature_id FROM literature_supplementarymaterial)"
        )
        return {citation_key for (citation_key,) in cursor.fetchall()}

    def convert(self, references, database):
        """Create an ``Item`` for each reference, each in its own savepoint.

        Args:
            references: The ``(primary key, CSL JSON dict)`` pairs to convert.
            database: The alias of the database to write to.

        Returns:
            One line per reference that could not be converted, naming its
            citation key and the reason.
        """
        failures = []
        for pk, data in references:
            try:
                with transaction.atomic(using=database):
                    from_csl_json(data, pk=pk)
            # Old rows hold whatever their JSON field was given, so a malformed value
            # surfaces as a type or attribute error, not only as a ValidationError.
            except (ValidationError, AttributeError, TypeError, ValueError) as error:
                failures.append(f"{data['citation-key']}: {error}")
        return failures

    def carry_timestamps(self, cursor):
        """Give each new ``Item`` the created and modified times of its old row.

        Args:
            cursor: A cursor on the database holding both tables.
        """
        cursor.execute(
            "UPDATE literature_item SET"
            " created = (SELECT created FROM literature_literatureitem old"
            " WHERE old.id = literature_item.id),"
            " modified = (SELECT modified FROM literature_literatureitem old"
            " WHERE old.id = literature_item.id)"
        )

    def repoint_foreign_keys(self, editor, database):
        """Point every host foreign key to ``Item`` at its table, returning their labels.

        Primary keys are kept, so the stored values are already right. Only the
        database constraint still names the old table. Altering the field from no
        constraint to one creates the constraint against ``literature_item``. The
        old constraint goes with the old table, which is dropped afterwards.

        Args:
            editor: The schema editor to alter the host tables with.
            database: The alias of the database being upgraded.

        Returns:
            The ``app_label.Model.field`` label of each field it pointed at ``Item``.
        """
        repointed = []
        for model in apps.get_models(include_auto_created=True):
            if (
                model._meta.app_label == "literature"
                or not model._meta.managed
                or not router.allow_migrate_model(database, model)
            ):
                continue
            for field in model._meta.local_fields:
                if field.related_model is Item and field.db_constraint:
                    unconstrained = copy.copy(field)
                    unconstrained.db_constraint = False
                    editor.alter_field(model, unconstrained, field)
                    repointed.append(f"{model._meta.label}.{field.name}")
        return repointed
