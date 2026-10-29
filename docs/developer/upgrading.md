# Upgrading from the `LiteratureItem` schema

Move a database that holds references in the old `LiteratureItem` schema to the current models,
keeping every reference and every link your own models have to one.

Before its current models, `literature` stored each reference as one `LiteratureItem` row holding
the reference's CSL JSON, with tags, collections and supplementary material beside it. That schema
was installed from the [SamuelJennings/django-literature](https://github.com/SamuelJennings/django-literature)
repository, and its migrations run from `0001_initial` to `0004_alter_literatureitem_options`. The
current models use the same app label and reuse two of those migration names, so `migrate` alone
cannot make the move. The `upgrade_literature` command makes it instead.

The releases published to PyPI before 0.1.9 are not covered. Up to 0.1.5 they shipped another
schema again, built around a `Literature` model, and 0.1.6 and 0.1.7 shipped no migrations at all.

## What the command does

In one transaction, so it either finishes or changes nothing, `upgrade_literature`:

- creates the current tables and records the current migrations as applied,
- converts every `LiteratureItem` from the CSL JSON it stored into an `Item` with its names, dates
  and identifiers, with the same primary key, citation key, type and created and modified times,
- adds the item's tags to its `keyword` field, after any keywords its JSON already held,
- points every foreign key from your own models to `Item` at the new table,
- drops the old tables.

Because each reference keeps its primary key, the values in your own foreign key columns stay
right, and no rows of yours are rewritten.

The current models have no place for collections, supplementary material or a file attached to a
reference. If any reference has one, the command stops before changing anything and names those
references. Run it again with `--discard-unconverted` to upgrade without them. The files
themselves stay in your storage.

The command accepts the forms that CSL JSON exporters such as Zotero commonly write. A DOI
written as a `doi.org` or `dx.doi.org` link or with a `doi:` prefix is stored as the bare DOI,
and an ISSN written without its hyphen is stored with it. A name listed twice under one role is
stored once.

If a reference cannot be converted, for example because its stored DOI is not a DOI, its ISSN
fails its check digit, or one field holds several ISSNs or ISBNs (an item stores one identifier of
each type), the command changes nothing and lists every such reference with the reason. Correct the JSON in the
`item` column of `literature_literatureitem`, or delete the row, and run it again.

## Before you start

Back up the database, and run the whole procedure against a copy of it first.

## 1. Point your own code at `Item`

Change every foreign key, one-to-one field and many-to-many field in your models that names
`literature.LiteratureItem` so that it names `literature.Item`:

```python
class Dataset(models.Model):
    reference = models.ForeignKey(
        "literature.Item",  # was "literature.LiteratureItem"
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
```

Then update the code that read the old model. `Item` stores the CSL JSON variables as fields and
related records rather than in one `item` dictionary. See [Data model](../reference/data-model.md) and, for
the DOI and year, `Item.doi` and `Item.year`.

## 2. Rewrite your migrations' references to the old schema

Your existing migrations still name the old model and the old migrations. Edit them in place:

- In `dependencies`, replace every `("literature", "<old migration>")` with
  `("literature", "0001_initial")`.
- In `operations`, replace `to="literature.literatureitem"` with `to="literature.item"`.

Run `python manage.py makemigrations --check`. It should find no changes. A migration it proposes
means one of your references to the old model was missed.

These edits change history that has already been applied, which is safe here because the command
leaves your tables matching the edited migrations. Do not create a new migration for the switch.

A `ManyToManyField` without a `through` model keeps its links in a join table whose column for
the reference is named `literatureitem_id`, while a field to `Item` expects `item_id`. The command
does not rename that column, and stops without changing anything when it finds one. Rename it to
`item_id` before running the command.

## 3. Upgrade the package and run the command

Install the current release, then run the command before anything else touches the database:

```bash
python manage.py upgrade_literature
python manage.py migrate
```

The command reports how many references it converted and which of your fields it pointed at the
new table. `migrate` then applies anything else that is pending and creates the permissions for
`Item`. If the literature tables live in a database other than `default`, pass
`--database <alias>` to the command.

## 4. Tidy up

The old models' content types remain in `django_content_type`. Remove them with:

```bash
python manage.py remove_stale_contenttypes
```

It asks before deleting, and lists anything that still refers to them, such as permissions
granted on the old models.
