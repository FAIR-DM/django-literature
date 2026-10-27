"""The ``LiteratureItem`` schema a database holds before ``upgrade_literature``.

Before this package's current models, ``literature`` shipped a different schema
under the same app label: one ``LiteratureItem`` table holding each reference's
CSL JSON whole, with tags, collections and supplementary material beside it. Its
migrations ran from ``0001_initial`` to ``0004_alter_literatureitem_options``.

``LEGACY_OPERATIONS`` builds that schema as it stood after ``0004``, adapted from
those four migrations: the rename of ``key`` to ``citation_key`` and the longer
``title`` are folded in, and the upload paths are plain strings because the
functions they named no longer exist. The last operation stands in for a host
project's own table, with a foreign key to ``LiteratureItem``.
"""

import django.db.models.deletion
import partial_date.fields
from django.db import migrations, models

#: The migrations a database on the ``LiteratureItem`` schema records as applied.
LEGACY_MIGRATIONS = (
    "0001_initial",
    "0002_rename_key_literatureitem_citation_key",
    "0003_alter_literatureitem_citation_key_and_more",
    "0004_alter_literatureitem_options",
)

#: Every table the ``LiteratureItem`` schema creates in the ``literature`` app.
LEGACY_TABLES = (
    "literature_collection",
    "literature_tag",
    "literature_literatureitem",
    "literature_literatureitem_collections",
    "literature_literatureitem_keyword",
    "literature_supplementarymaterial",
)


def id_field():
    return models.BigAutoField(
        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
    )


#: ``(app_label, operation)`` pairs, applied in order.
LEGACY_OPERATIONS = [
    (
        "literature",
        migrations.CreateModel(
            name="Collection",
            fields=[
                ("id", id_field()),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("modified", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField()),
            ],
        ),
    ),
    (
        "literature",
        migrations.CreateModel(
            name="Tag",
            fields=[
                ("id", id_field()),
                ("name", models.CharField(max_length=255, unique=True)),
            ],
        ),
    ),
    (
        "literature",
        migrations.CreateModel(
            name="LiteratureItem",
            fields=[
                ("id", id_field()),
                ("citation_key", models.CharField(max_length=255, unique=True)),
                ("type", models.CharField(max_length=22)),
                (
                    "title",
                    models.CharField(
                        blank=True, db_index=True, max_length=1000, null=True
                    ),
                ),
                ("issued", partial_date.fields.PartialDateField(blank=True, null=True)),
                ("item", models.JSONField(default=dict)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("modified", models.DateTimeField(auto_now=True)),
                (
                    "file",
                    models.FileField(blank=True, null=True, upload_to="literature/"),
                ),
                (
                    "collections",
                    models.ManyToManyField(blank=True, to="literature.collection"),
                ),
                ("keyword", models.ManyToManyField(blank=True, to="literature.tag")),
            ],
        ),
    ),
    (
        "literature",
        migrations.CreateModel(
            name="SupplementaryMaterial",
            fields=[
                ("id", id_field()),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("modified", models.DateTimeField(auto_now=True)),
                ("file", models.FileField(upload_to="supplementary/")),
                (
                    "literature",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="supplementary",
                        to="literature.literatureitem",
                    ),
                ),
            ],
        ),
    ),
    (
        "host",
        migrations.CreateModel(
            name="Citation",
            fields=[
                ("id", id_field()),
                (
                    "reference",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="literature.literatureitem",
                    ),
                ),
            ],
        ),
    ),
    (
        "host",
        migrations.CreateModel(
            name="ReadingListEntry",
            fields=[
                ("id", id_field()),
                (
                    "reference",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="literature.literatureitem",
                    ),
                ),
            ],
        ),
    ),
]
