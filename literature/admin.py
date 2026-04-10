"""Django admin configuration for the literature app."""

import datetime

from django.contrib import admin
from django.db.models import DateTimeField, OuterRef, Subquery
from django.db.models.functions import Cast, ExtractYear
from django.utils.translation import gettext_lazy as _
from ordered_model.admin import OrderedInlineModelAdminMixin, OrderedTabularInline

from literature.models import Item, ItemDate, ItemIdentifier, ItemName, Name


class ItemNameInline(OrderedTabularInline):
    model = ItemName
    fields = ("name", "role", "order", "move_up_down_links")
    readonly_fields = ("order", "move_up_down_links")
    extra = 1
    ordering = ("order",)
    verbose_name = _("contributor")
    verbose_name_plural = _("contributors")


class ItemDateInline(admin.TabularInline):
    model = ItemDate
    fields = ("date_type", "begin", "end", "season", "circa", "literal", "raw")
    extra = 1
    verbose_name = _("date")
    verbose_name_plural = _("dates")


class ItemIdentifierInline(admin.TabularInline):
    model = ItemIdentifier
    fields = ("type", "value")
    extra = 1
    verbose_name = _("identifier")
    verbose_name_plural = _("identifiers")


class IssuedYearFilter(admin.SimpleListFilter):
    title = _("year")
    parameter_name = "issued_year"

    def lookups(self, request, model_admin):
        years = (
            ItemDate.objects.filter(date_type="issued")
            .annotate(
                year=ExtractYear(
                    Cast("begin", output_field=DateTimeField()),
                    tzinfo=datetime.timezone.utc,
                )
            )
            .values_list("year", flat=True)
            .distinct()
            .order_by("-year")
        )
        return [(str(y), str(y)) for y in years if y is not None]

    def queryset(self, request, queryset):
        if self.value():
            matching_pks = (
                ItemDate.objects.filter(date_type="issued")
                .annotate(
                    year=ExtractYear(
                        Cast("begin", output_field=DateTimeField()),
                        tzinfo=datetime.timezone.utc,
                    )
                )
                .filter(year=int(self.value()))
                .values_list("item_id", flat=True)
            )
            return queryset.filter(pk__in=matching_pks)
        return queryset


@admin.register(Item)
class ItemAdmin(OrderedInlineModelAdminMixin, admin.ModelAdmin):
    list_display = ("title_display", "type", "issued_year", "citation_key")
    search_fields = ("title", "citation_key")
    list_filter = ("type", IssuedYearFilter, "publisher")
    ordering = ("-created",)
    readonly_fields = ("created", "modified")
    inlines = [ItemNameInline, ItemDateInline, ItemIdentifierInline]

    fieldsets = [
        (
            _("Identity & Type"),
            {"fields": ("citation_key", "type")},
        ),
        (
            _("Titles"),
            {"fields": ("title", "title_short", "container_title", "container_title_short")},
        ),
        (
            _("Publication"),
            {"fields": ("publisher", "publisher_place")},
        ),
        (
            _("Numbering"),
            {
                "classes": ["collapse"],
                "fields": (
                    "volume",
                    "issue",
                    "page",
                    "page_first",
                    "number",
                    "number_of_pages",
                    "number_of_volumes",
                    "edition",
                    "version",
                    "chapter_number",
                    "collection_number",
                    "section",
                    "part",
                    "supplement",
                    "printing",
                ),
            },
        ),
        (
            _("Additional Titles"),
            {
                "classes": ["collapse"],
                "fields": (
                    "original_title",
                    "collection_title",
                    "volume_title",
                    "volume_title_short",
                    "part_title",
                    "reviewed_title",
                    "reviewed_genre",
                ),
            },
        ),
        (
            _("Content"),
            {"classes": ["collapse"], "fields": ("abstract", "note", "annote")},
        ),
        (
            _("Event"),
            {"classes": ["collapse"], "fields": ("event_title", "event_place")},
        ),
        (
            _("Original Publication"),
            {"classes": ["collapse"], "fields": ("original_publisher", "original_publisher_place")},
        ),
        (
            _("Archive & Location"),
            {
                "classes": ["collapse"],
                "fields": (
                    "archive",
                    "archive_collection",
                    "archive_location",
                    "archive_place",
                    "authority",
                    "jurisdiction",
                    "call_number",
                    "dimensions",
                    "division",
                    "scale",
                    "source",
                    "references",
                ),
            },
        ),
        (
            _("Citation Metadata"),
            {
                "classes": ["collapse"],
                "fields": (
                    "journal_abbreviation",
                    "citation_label",
                    "citation_number",
                    "first_reference_note_number",
                    "locator",
                    "year_suffix",
                ),
            },
        ),
        (
            _("Classification & Keywords"),
            {
                "classes": ["collapse"],
                "fields": ("language", "genre", "medium", "status", "keyword", "categories", "custom"),
            },
        ),
        (
            _("Record Info"),
            {"classes": ["collapse"], "fields": ("created", "modified")},
        ),
    ]

    @admin.display(description=_("title"))
    def title_display(self, obj):
        return str(obj)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        issued_year_subquery = (
            ItemDate.objects.filter(item=OuterRef("pk"), date_type="issued")
            .annotate(
                year=ExtractYear(
                    Cast("begin", output_field=DateTimeField()),
                    tzinfo=datetime.timezone.utc,
                )
            )
            .values("year")[:1]
        )
        return qs.annotate(issued_year=Subquery(issued_year_subquery))

    @admin.display(description=_("year"), ordering="issued_year")
    def issued_year(self, obj):
        year = obj.issued_year
        return year if year is not None else "—"


@admin.register(Name)
class NameAdmin(admin.ModelAdmin):
    list_display = ("family", "given", "literal")
    search_fields = ("family", "given", "literal")
