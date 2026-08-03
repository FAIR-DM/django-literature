"""Django models for the literature app.

Provides a normalized representation of the CSL JSON 1.0.2 bibliographic
data format as relational database tables.

Models:
    Item          — CSL JSON top-level item object (all scalar fields)
    Name          — CSL JSON name-variable definition (name parts)
    ItemName      — Ordered through-model linking Name to Item with a role
    ItemDate      — CSL JSON date-variable instance per item
    ItemIdentifier — Typed identifier (DOI, ISBN, etc.) per item

Reference: https://resource.citationstyles.org/schema/v1.0/input/json/csl-data.json
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from partial_date import PartialDate  # noqa: F401  used in type hints
from partial_date.fields import PartialDateField

from literature.choices import DateType, ItemType, NameRole
from literature.validators import validate_identifier


class Item(models.Model):
    """CSL JSON top-level item object.

    Stores all scalar/string/number CSL JSON fields as columns.
    Name-variables, date-variables, and identifiers are stored in
    related models (ItemName, ItemDate, ItemIdentifier).

    CSL JSON mapping: top-level item object
    Reference: https://resource.citationstyles.org/schema/v1.0/input/json/csl-data.json
    """

    # --- Identity & type ---
    citation_key = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name=_("citation key"),
        help_text=_("CSL JSON: citation-key (or id fallback). Unique per import batch."),
    )
    type = models.CharField(
        max_length=30,
        choices=ItemType.choices,
        verbose_name=_("type"),
        db_index=True,
        help_text=_("CSL JSON: type"),
    )

    # --- Titles ---
    title = models.CharField(
        max_length=1000,
        blank=True,
        db_index=True,
        verbose_name=_("title"),
        help_text=_("CSL JSON: title"),
    )
    title_short = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_("short title"),
        help_text=_("CSL JSON: title-short (also imports deprecated shortTitle)"),
    )
    original_title = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_("original title"),
        help_text=_("CSL JSON: original-title"),
    )
    container_title = models.CharField(
        max_length=500,
        blank=True,
        db_index=True,
        verbose_name=_("container title"),
        help_text=_("CSL JSON: container-title"),
    )
    container_title_short = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("container title short"),
        help_text=_("CSL JSON: container-title-short"),
    )
    collection_title = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_("collection title"),
        help_text=_("CSL JSON: collection-title"),
    )
    volume_title = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_("volume title"),
        help_text=_("CSL JSON: volume-title"),
    )
    volume_title_short = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("volume title short"),
        help_text=_("CSL JSON: volume-title-short"),
    )
    part_title = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_("part title"),
        help_text=_("CSL JSON: part-title"),
    )
    reviewed_title = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_("reviewed title"),
        help_text=_("CSL JSON: reviewed-title"),
    )
    reviewed_genre = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("reviewed genre"),
        help_text=_("CSL JSON: reviewed-genre"),
    )

    # --- Long-text fields ---
    abstract = models.TextField(
        blank=True,
        verbose_name=_("abstract"),
        help_text=_("CSL JSON: abstract"),
    )
    note = models.TextField(
        blank=True,
        verbose_name=_("note"),
        help_text=_("CSL JSON: note"),
    )
    annote = models.TextField(
        blank=True,
        verbose_name=_("annotation"),
        help_text=_("CSL JSON: annote"),
    )

    # --- Publisher ---
    publisher = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        verbose_name=_("publisher"),
        help_text=_("CSL JSON: publisher"),
    )
    publisher_place = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("publisher place"),
        help_text=_("CSL JSON: publisher-place"),
    )
    original_publisher = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("original publisher"),
        help_text=_("CSL JSON: original-publisher"),
    )
    original_publisher_place = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("original publisher place"),
        help_text=_("CSL JSON: original-publisher-place"),
    )

    # --- Event ---
    event_title = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_("event title"),
        help_text=_("CSL JSON: event-title (also imports deprecated event)"),
    )
    event_place = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("event place"),
        help_text=_("CSL JSON: event-place"),
    )

    # --- Volume/issue/page/number ---
    volume = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("volume"),
        help_text=_("CSL JSON: volume (string-or-number stored as string)"),
    )
    issue = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("issue"),
        help_text=_("CSL JSON: issue (string-or-number stored as string)"),
    )
    page = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("page"),
        help_text=_("CSL JSON: page (e.g. '171-175')"),
    )
    page_first = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("page first"),
        help_text=_("CSL JSON: page-first (string-or-number stored as string)"),
    )
    number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("number"),
        help_text=_("CSL JSON: number"),
    )
    number_of_pages = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("number of pages"),
        help_text=_("CSL JSON: number-of-pages (string-or-number stored as string)"),
    )
    number_of_volumes = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("number of volumes"),
        help_text=_("CSL JSON: number-of-volumes (string-or-number stored as string)"),
    )
    edition = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("edition"),
        help_text=_("CSL JSON: edition (string-or-number, e.g. '2nd', 3)"),
    )
    version = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("version"),
        help_text=_("CSL JSON: version"),
    )
    chapter_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("chapter number"),
        help_text=_("CSL JSON: chapter-number (string-or-number stored as string)"),
    )
    collection_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("collection number"),
        help_text=_("CSL JSON: collection-number (string-or-number stored as string)"),
    )
    section = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("section"),
        help_text=_("CSL JSON: section"),
    )
    part = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("part"),
        help_text=_("CSL JSON: part (string-or-number stored as string)"),
    )
    supplement = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("supplement"),
        help_text=_("CSL JSON: supplement (string-or-number stored as string)"),
    )
    printing = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("printing"),
        help_text=_("CSL JSON: printing (string-or-number stored as string)"),
    )

    # --- Status / metadata ---
    status = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("status"),
        help_text=_("CSL JSON: status"),
    )
    medium = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("medium"),
        help_text=_("CSL JSON: medium"),
    )
    genre = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("genre"),
        help_text=_("CSL JSON: genre"),
    )
    language = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_("language"),
        help_text=_("CSL JSON: language (BCP 47 tag, e.g. 'en')"),
    )

    # --- Archive ---
    archive = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("archive"),
        help_text=_("CSL JSON: archive"),
    )
    archive_collection = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("archive collection"),
        help_text=_("CSL JSON: archive_collection (note: underscored in CSL JSON)"),
    )
    archive_location = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("archive location"),
        help_text=_("CSL JSON: archive_location (note: underscored in CSL JSON)"),
    )
    archive_place = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("archive place"),
        help_text=_("CSL JSON: archive-place"),
    )
    authority = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("authority"),
        help_text=_("CSL JSON: authority"),
    )
    jurisdiction = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("jurisdiction"),
        help_text=_("CSL JSON: jurisdiction"),
    )
    call_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("call number"),
        help_text=_("CSL JSON: call-number"),
    )
    dimensions = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("dimensions"),
        help_text=_("CSL JSON: dimensions"),
    )
    division = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("division"),
        help_text=_("CSL JSON: division"),
    )
    scale = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("scale"),
        help_text=_("CSL JSON: scale"),
    )
    source = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("source"),
        help_text=_("CSL JSON: source"),
    )
    references = models.TextField(
        blank=True,
        verbose_name=_("references"),
        help_text=_("CSL JSON: references"),
    )

    # --- Citation metadata (processor-generated or round-trip) ---
    journal_abbreviation = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("journal abbreviation"),
        help_text=_("CSL JSON: journalAbbreviation (camelCase in CSL JSON)"),
    )
    citation_label = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("citation label"),
        help_text=_("CSL JSON: citation-label (processor-generated; stored for round-trip)"),
    )
    citation_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("citation number"),
        help_text=_("CSL JSON: citation-number (string-or-number stored as string)"),
    )
    first_reference_note_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("first reference note number"),
        help_text=_("CSL JSON: first-reference-note-number (string-or-number stored as string)"),
    )
    locator = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("locator"),
        help_text=_("CSL JSON: locator (string-or-number stored as string)"),
    )
    year_suffix = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_("year suffix"),
        help_text=_("CSL JSON: year-suffix"),
    )

    # --- Keywords and free-form ---
    keyword = models.TextField(
        blank=True,
        verbose_name=_("keyword"),
        help_text=_("CSL JSON: keyword (single comma-separated string)"),
    )

    # --- JSON fields ---
    categories = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_("categories"),
        help_text=_("CSL JSON: categories (string array)"),
    )
    custom = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_("custom"),
        help_text=_("CSL JSON: custom (arbitrary key-value pairs)"),
    )

    # --- Auto timestamps (not in CSL JSON) ---
    created = models.DateTimeField(auto_now_add=True, verbose_name=_("created"))
    modified = models.DateTimeField(auto_now=True, verbose_name=_("modified"))

    class Meta:
        verbose_name = _("item")
        verbose_name_plural = _("items")
        ordering = ["-created"]

    def __str__(self) -> str:
        """Return truncated title (≤80 chars), falling back to citation_key."""
        if self.title:
            return self.title[:80] + "…" if len(self.title) > 80 else self.title
        return self.citation_key


class Name(models.Model):
    """CSL JSON name-variable definition.

    Stores all constituent parts of a personal or institutional name as
    defined in the CSL JSON 1.0.2 name-variable schema. Names are
    shared across items; the ItemName through-model records the role
    and ordered position.

    CSL JSON mapping: name-variable object
    """

    family = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("family name"),
        help_text=_("CSL JSON: family"),
    )
    given = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("given name"),
        help_text=_("CSL JSON: given"),
    )
    dropping_particle = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("dropping particle"),
        help_text=_("CSL JSON: dropping-particle (e.g. 'von', 'van')"),
    )
    non_dropping_particle = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("non-dropping particle"),
        help_text=_("CSL JSON: non-dropping-particle (e.g. 'van der', 'de')"),
    )
    suffix = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("suffix"),
        help_text=_("CSL JSON: suffix (e.g. 'Jr.', 'III')"),
    )
    literal = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_("literal"),
        help_text=_("CSL JSON: literal (institutional names or unparsed strings)"),
    )
    comma_suffix = models.BooleanField(
        default=False,
        verbose_name=_("comma suffix"),
        help_text=_("CSL JSON: comma-suffix"),
    )
    static_ordering = models.BooleanField(
        default=False,
        verbose_name=_("static ordering"),
        help_text=_("CSL JSON: static-ordering (e.g. for East Asian names)"),
    )
    parse_names = models.BooleanField(
        default=False,
        verbose_name=_("parse names"),
        help_text=_("CSL JSON: parse-names (signal to CSL processor)"),
    )
    created = models.DateTimeField(auto_now_add=True, verbose_name=_("created"))
    modified = models.DateTimeField(auto_now=True, verbose_name=_("modified"))

    class Meta:
        verbose_name = _("name")
        verbose_name_plural = _("names")
        indexes = [
            models.Index(fields=["family", "given"], name="name_family_given_idx"),
        ]

    def __str__(self) -> str:
        """Return 'family, given' or literal when family/given are empty."""
        if self.family or self.given:
            parts = filter(None, [self.family, self.given])
            return ", ".join(parts)
        return self.literal or f"Name #{self.pk}"


class ItemName(models.Model):
    """Ordered through-model linking Name to Item with a contributor role.

    Provides explicit position ordering of contributors within each
    ``(item, role)`` scope via the ``order`` field: the author list, the
    editor list, and so on are each numbered independently from zero, so
    reordering one role never disturbs another. The position is assigned in
    :meth:`save` on first insert. See ADR-0005.

    CSL JSON mapping: name-variable array entries on a bibliographic item
    (e.g. author array, editor array).
    """

    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="item_names",
        verbose_name=_("item"),
        help_text=_("The bibliographic item this name is associated with."),
    )
    name = models.ForeignKey(
        Name,
        on_delete=models.CASCADE,
        related_name="item_names",
        verbose_name=_("name"),
        help_text=_("The name record for this contributor."),
    )
    role = models.CharField(
        max_length=30,
        choices=NameRole.choices,
        verbose_name=_("role"),
        help_text=_("CSL JSON name-variable field (e.g. author, editor, translator)."),
    )
    order = models.PositiveIntegerField(
        editable=False,
        verbose_name=_("order"),
        help_text=_("Position of this contributor within the (item, role) group."),
    )

    class Meta:
        verbose_name = _("item name")
        verbose_name_plural = _("item names")
        ordering = ["item", "role", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["item", "role", "name"],
                name="unique_name_per_role_per_item",
            )
        ]
        indexes = [
            models.Index(fields=["item", "role", "order"], name="itemname_item_role_order_idx"),
            models.Index(fields=["name", "role"], name="itemname_name_role_idx"),
        ]

    def save(self, *args, **kwargs):
        """Assign a role-scoped position on first insert.

        ``order`` is numbered per ``(item, role)`` group, so the contributor
        list for each role is ordered independently. A new row is appended to
        the end of its own role's sequence; existing rows keep their position.
        """
        if self._state.adding and self.order is None:
            last = (
                ItemName.objects.filter(item=self.item, role=self.role).aggregate(models.Max("order")).get("order__max")
            )
            self.order = 0 if last is None else last + 1
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        """Return '<name> as <role> on <item>'."""
        return f"{self.name} as {self.role} on {self.item}"


class ItemDate(models.Model):
    """CSL JSON date-variable instance for a specific date slot on an item.

    Stores partial dates using django-partial-date's PartialDateField,
    supporting year-only, year-month, and full-date precision. Date ranges
    are represented by setting both begin and end.

    CSL JSON mapping: date-variable object keyed by date-variable slot name
    (e.g. 'issued', 'accessed', 'event-date').
    """

    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="item_dates",
        verbose_name=_("item"),
        help_text=_("The bibliographic item this date belongs to."),
    )
    date_type = models.CharField(
        max_length=20,
        choices=DateType.choices,
        verbose_name=_("date type"),
        help_text=_("CSL JSON date-variable slot (e.g. issued, accessed, event-date)."),
    )
    begin = PartialDateField(
        null=True,
        blank=True,
        verbose_name=_("begin date"),
        help_text=_("CSL JSON: date-parts[0] — start or single date with partial-date precision."),
    )
    end = PartialDateField(
        null=True,
        blank=True,
        verbose_name=_("end date"),
        help_text=_("CSL JSON: date-parts[1] — end date for ranges. Must not be set without begin."),
    )
    season = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_("season"),
        help_text=_("CSL JSON: season ('1'=Spring, '2'=Summer, '3'=Autumn, '4'=Winter or custom)"),
    )
    circa = models.BooleanField(
        default=False,
        verbose_name=_("circa"),
        help_text=_("CSL JSON: circa — approximate date flag."),
    )
    literal = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("literal"),
        help_text=_("CSL JSON: literal — free-text date when structured representation is impossible."),
    )
    raw = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("raw"),
        help_text=_("CSL JSON: raw — unparsed date string from source."),
    )
    raw_date_parts = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_("raw date parts"),
        help_text=_("CSL JSON: date-parts — stores original array when normalization to PartialDate fails."),
    )

    class Meta:
        verbose_name = _("item date")
        verbose_name_plural = _("item dates")
        constraints = [
            models.UniqueConstraint(
                fields=["item", "date_type"],
                name="unique_date_type_per_item",
            )
        ]
        indexes = [
            models.Index(fields=["item", "date_type"], name="itemdate_item_date_type_idx"),
            models.Index(fields=["begin"], name="itemdate_begin_idx"),
            models.Index(fields=["end"], name="itemdate_end_idx"),
        ]

    def __str__(self) -> str:
        """Return '<date_type>: <begin>' or just the date_type."""
        if self.begin:
            return f"{self.date_type}: {self.begin}"
        if self.literal:
            return f"{self.date_type}: {self.literal}"
        return self.date_type


class ItemIdentifier(models.Model):
    """Typed identifier record for a bibliographic item.

    Stores DOI, ISBN, ISSN, PMID, PMCID, URL and any other identifier
    type as a (type, value) pair linked to an Item.

    The type field intentionally does NOT use choices= validation — this
    allows unknown identifier type strings to be stored without rejection,
    satisfying FR-017. The IdentifierType enum provides known values for
    lookup and documentation only.

    Design note: the (item, type) uniqueness constraint means each item
    stores at most one identifier per type. Multiple ISBNs (ISBN-10 +
    ISBN-13) are out of scope for this feature.

    CSL JSON mapping: DOI, ISBN, ISSN, PMID, PMCID, URL top-level fields;
    unknown types placed in the custom object on export.
    """

    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="item_identifiers",
        verbose_name=_("item"),
        help_text=_("The bibliographic item this identifier belongs to."),
    )
    type = models.CharField(
        max_length=50,
        verbose_name=_("identifier type"),
        help_text=_("Identifier type string (e.g. DOI, ISBN, ISSN, PMID, PMCID, URL, arXiv)."),
    )
    value = models.CharField(
        max_length=500,
        verbose_name=_("value"),
        help_text=_("The identifier value string."),
    )

    class Meta:
        verbose_name = _("item identifier")
        verbose_name_plural = _("item identifiers")
        constraints = [
            models.UniqueConstraint(
                fields=["item", "type"],
                name="unique_identifier_type_per_item",
            )
        ]
        indexes = [
            models.Index(fields=["item", "type"], name="itemidentifier_item_type_idx"),
            models.Index(fields=["type", "value"], name="itemidentifier_type_value_idx"),
            models.Index(fields=["value"], name="itemidentifier_value_idx"),
        ]

    def __str__(self) -> str:
        """Return '<type>: <value>'."""
        return f"{self.type}: {self.value}"

    def clean(self) -> None:
        """Validate identifier value format for known identifier types (FR-020).

        Unknown identifier types skip validation.
        """
        validate_identifier(self.type, self.value)
        super().clean()

    def save(self, *args, **kwargs):
        """Validate the identifier format before writing (FR-020).

        ``clean()`` alone only runs when a caller invokes ``full_clean()``, so a
        direct ``objects.create()`` or instance ``save()`` would otherwise store
        a malformed value. Validating here means every write path that goes
        through ``save()`` applies the same rules. ``bulk_create()`` skips
        ``save()`` and remains unchecked, as it does for any Django model.
        """
        validate_identifier(self.type, self.value)
        return super().save(*args, **kwargs)
