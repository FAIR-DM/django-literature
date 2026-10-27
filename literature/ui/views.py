"""Views for the opt-in front end."""

import json
from functools import cached_property

from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Case, IntegerField, Prefetch, Q, Value, When
from django.forms import MultiWidget
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views import View
from django_tomselect.autocompletes import AutocompleteModelView
from mvp.integrations.django_tables.views import MVPTableView
from mvp.views import (
    MVPCreateView,
    MVPDeleteView,
    MVPDetailView,
    MVPFormView,
    MVPListView,
    MVPUpdateView,
    PageWidth,
)

from literature.choices import ItemType, NameRole
from literature.importers import get_format
from literature.importers.results import Outcome
from literature.models import Item, ItemName, Name
from literature.ui.contributors import contributor_groups, stored_contributor_names
from literature.ui.fieldgroups import TYPE_DATE_SLOTS, TYPE_ROLES, FieldGroups
from literature.ui.fields import field_sections
from literature.ui.filters import ItemFilterSet, ItemTableFilterSet
from literature.ui.formlayout import DATE_SLOTS, date_field_name
from literature.ui.forms import (
    CONTRIBUTOR_NAMES_DATALIST_ID,
    ConfirmImportForm,
    ImportForm,
    ItemForm,
)
from literature.ui.importing import ImportReport
from literature.ui.inlines import CONTRIBUTOR_INLINES, IdentifierInline
from literature.ui.links import web_url
from literature.ui.picker import item_label
from literature.ui.staging import StagedUpload
from literature.ui.tables import ImportReportTable, ItemTable, OutcomeColumn
from literature.utils.doi import doi_url

#: The most references one search answers with.
SEARCH_LIMIT = 20

#: The most characters of a search the view reads; the rest is dropped.
SEARCH_TEXT_LIMIT = 200

#: The related-row sets composed on both the create and update pages.
ITEM_INLINES = [*CONTRIBUTOR_INLINES, IdentifierInline]

#: What the catalogue calls itself wherever a reader is shown its name. Set here
#: because renaming the model would also rename it in the admin and migrations.
CATALOGUE_TITLE = _("Publications")

#: The same word mid-sentence, a message of its own because lowercasing is wrong
#: for languages that capitalise their nouns.
CATALOGUE_NAME_PLURAL = _("publications")

#: CRUD action to namespaced URL name, shared by every view: under this app's
#: ``app_name`` a bare ``reverse("item-list")`` raises ``NoReverseMatch``.
CRUD_VIEWS = {
    "list": "literature:{model_name}-list",
    "detail": "literature:{model_name}-detail",
    "create": "literature:{model_name}-create",
    "update": "literature:{model_name}-update",
    "delete": "literature:{model_name}-delete",
    "import": "literature:{model_name}-import",
}

#: The model permission each write page asks for. Importing creates
#: references, so it asks for the same permission as adding one.
ADD_PERMISSION = "literature.add_item"
CHANGE_PERMISSION = "literature.change_item"
DELETE_PERMISSION = "literature.delete_item"


class HasPermission:
    """A ``show_<action>_action`` flag that draws a link only for users holding *permission*.

    django-mvp calls a callable flag with the request user. Hiding the link is
    courtesy only: the page it points at checks the same permission itself.

    Args:
        permission: The permission to check, such as ``"literature.add_item"``.
    """

    def __init__(self, permission):
        self.permission = permission

    def __call__(self, user):
        """Return whether *user* holds the permission.

        Args:
            user: The signed-in user.

        Returns:
            ``True`` if the user holds the permission.
        """
        return user.has_perm(self.permission)


#: Every ``ItemType`` value mapped to the group names its form shows by default,
#: serialised once into every write page.
TYPE_GROUPS_JSON = json.dumps(
    {
        item_type: sorted(FieldGroups.groups_for(item_type))
        for item_type in ItemType.values
    }
)


#: The date slots and contributor roles each type leads with, serialised once
#: into every write page beside ``TYPE_GROUPS_JSON``.
TYPE_DATES_JSON = json.dumps(
    {item_type: sorted(slots) for item_type, slots in TYPE_DATE_SLOTS.items()}
)
TYPE_ROLES_JSON = json.dumps(
    {item_type: sorted(roles) for item_type, roles in TYPE_ROLES.items()}
)


def field_group_context(form, inlines, forced_groups=frozenset()):
    """Build the write form's template context.

    A group holding a field with an error joins the forced groups, so an error is
    never drawn inside a section the page has hidden.

    Args:
        form: The bound or unbound ``ItemForm``.
        inlines: The contributor sets followed by the identifier set.
        forced_groups: Groups already holding a value on the object being edited
            (``FieldGroups.groups_holding_values``), shown whatever the item type.

    Returns:
        The context entries the write form's template reads.
    """
    with_errors = {
        group
        for group, names in FieldGroups.GROUPS.items()
        if any(name in form.errors for name in names)
    }
    *contributor_sets, identifier_set = inlines
    # The identifier set fills a tab whose label already names it, so it draws no heading.
    identifier_set.is_whole_page = True
    dates_with_errors = {
        slot
        for slot, _label in DATE_SLOTS
        if date_field_name(slot) in form.errors
        or date_field_name(slot, end=True) in form.errors
    }
    roles_held = {
        formset.prefix.removeprefix("contributors-")
        for formset in contributor_sets
        if any(row.instance.pk or row.errors for row in formset.forms)
    }
    return {
        "type_groups_json": TYPE_GROUPS_JSON,
        "forced_groups_json": json.dumps(sorted(forced_groups | with_errors)),
        "type_dates_json": TYPE_DATES_JSON,
        "forced_dates_json": json.dumps(
            sorted(form.date_slots_holding_values() | dates_with_errors)
        ),
        "type_roles_json": TYPE_ROLES_JSON,
        "forced_roles_json": json.dumps(sorted(roles_held)),
        "contributor_sets": contributor_sets,
        "identifier_set": identifier_set,
        "problems": form_problems(form, inlines),
    }


def form_problems(form, inlines):
    """Collect every error on the page, in page order, each with the id of the field to fix.

    Drawn as one summary above the form, since an error may sit in a tab the
    person is not looking at.

    Args:
        form: The bound ``ItemForm``.
        inlines: The contributor sets followed by the identifier set.

    Returns:
        A list of ``{"message", "target"}`` dicts; ``target`` is empty for an
        error that belongs to no field.
    """
    problems = []
    for message in form.non_field_errors():
        problems.append({"message": message, "target": ""})
    for bound in form:
        label = bound.label
        if bound.name.startswith("date_") and bound.name.endswith("_end"):
            label = form[bound.name.removesuffix("_end")].label
        # A widget in parts, such as a partial date, gives its first part the id.
        target = bound.auto_id
        if isinstance(bound.field.widget, MultiWidget):
            target = f"{target}_0"
        for message in bound.errors:
            problems.append({"message": f"{label}: {message}", "target": target})
    for formset in inlines:
        for message in formset.non_form_errors():
            problems.append({"message": message, "target": ""})
        for row in formset.forms:
            if not row.errors:
                continue
            first = next(iter(row.visible_fields()), None)
            target = first.auto_id if first else ""
            for message in row.non_field_errors():
                problems.append(
                    {"message": f"{formset.title}: {message}", "target": target}
                )
            for bound in row:
                for message in bound.errors:
                    problems.append(
                        {
                            "message": f"{formset.title}, {bound.label}: {message}",
                            "target": bound.auto_id,
                        }
                    )
    return problems


def contributor_datalist_context():
    """Build the stored-name suggestions a contributor row's input reads via ``list=``.

    Returns:
        The datalist id and the family names to offer.
    """
    return {
        "contributor_names_datalist_id": CONTRIBUTOR_NAMES_DATALIST_ID,
        "contributor_names": stored_contributor_names(),
    }


class CatalogueListMixin:
    """The card-list configuration ``ItemListView`` and ``ContributorDetailView`` share.

    Subclassing ``ItemListView`` directly would hand the contributor page a
    search box and filters it must not have.
    """

    model = Item
    page_title = CATALOGUE_TITLE
    # The reference component in a card, so a project's own pages show a reference the same way.
    list_item_template = "literature/ui/item_list_item.html"

    # A directory entry shows nothing without its show_<action>_action flag. No
    # create_form_class, so Add renders a plain link rather than a modal.
    directory: list[str] = ["create"]
    show_create_action = HasPermission(ADD_PERMISSION)
    crud_views = CRUD_VIEWS

    def get_queryset(self):
        """Prefetch what the reference component reads, for a constant query count."""
        return (
            super()
            .get_queryset()
            .prefetch_related("item_names__name", "item_dates", "item_identifiers")
        )

    def get_model_info(self):
        """Name the collection ``CATALOGUE_NAME_PLURAL``, not the model's own name."""
        return {
            **super().get_model_info(),
            "verbose_name_plural": CATALOGUE_NAME_PLURAL,
        }


class ItemListView(CatalogueListMixin, MVPListView):
    """The catalogue list (FS-006, #55)."""

    filterset_class = ItemFilterSet
    toolbar_filters = ["q"]
    # The filters are a drawer at every width, never a column beside the list.
    filter_panel_attrs = {"position": "end", "breakpoint": False}

    empty_state_heading = _("Nothing in the catalogue yet")
    empty_state_message = _("References imported or created will appear here.")

    directory: list[str] = ["create", "import"]
    show_import_action = HasPermission(ADD_PERMISSION)

    def get_url_kwargs(self, action):
        """Resolve "import" as collection-level, like the "list"/"create" default."""
        # A list view's empty self.kwargs would otherwise leave directory.import_url unresolved.
        if action == "import":
            return {}
        return super().get_url_kwargs(action)


class ItemTableView(MVPTableView):
    """The catalogue as a table (FS-009, #87).

    ``urls.py`` points the ``item-list`` route at it by default
    (docs/adr/0033-the-catalogue-view-is-chosen-by-a-setting.md).
    """

    model = Item
    table_class = ItemTable

    # 24 matches the card list; with no page size the table renders every row.
    paginate_by = 24

    page_title = CATALOGUE_TITLE

    # Adds Import to the end of the toolbar row, after the Filters button.
    template_name = "literature/ui/item_table_page.html"
    toolbar_filters = ["q", "type", "issued_year", "language"]
    directory: list[str] = ["create", "import"]
    show_create_action = HasPermission(ADD_PERMISSION)
    show_import_action = HasPermission(ADD_PERMISSION)
    crud_views = CRUD_VIEWS
    filterset_class = ItemTableFilterSet
    filter_panel_attrs = {"position": "end", "breakpoint": False}

    # No order_by: MVPTableViewMixin raises ImproperlyConfigured if it finds one.

    def get_url_kwargs(self, action):
        """Resolve "import" as collection-level, like the "list"/"create" default."""
        if action == "import":
            return {}
        return super().get_url_kwargs(action)

    empty_state_heading = _("Nothing in the catalogue yet")
    empty_state_message = _("References imported or created will appear here.")

    def get_queryset(self):
        """Prefetch what the credited-names and issued cells read."""
        # No "issued" annotation: ItemFilterSet.filter_queryset() already adds it.
        return (
            super()
            .get_queryset()
            .prefetch_related(
                Prefetch(
                    "item_names",
                    queryset=ItemName.objects.filter(
                        role__in=(NameRole.AUTHOR, NameRole.EDITOR)
                    ).select_related("name"),
                    to_attr="contributors",
                ),
                "item_dates",
            )
        )

    def get_model_info(self):
        """Name the collection ``CATALOGUE_NAME_PLURAL``, not the model's own name."""
        return {
            **super().get_model_info(),
            "verbose_name_plural": CATALOGUE_NAME_PLURAL,
        }

    def get_context_data(self, **kwargs):
        """Leave out empty choices, and draw the hidden ``sort`` field in the toolbar's form."""
        context = super().get_context_data(**kwargs)
        # A choice with no stored values (Language, say) offers nothing to pick. A panel
        # holding only the hidden field would add a Filters button that opens nothing.
        if "toolbar_fields" in context:
            context["toolbar_fields"] = [
                f
                for f in context["toolbar_fields"]
                if f["kind"] not in ("choice", "multichoice") or f["choices"]
            ]
        if "panel_fields" in context:
            context["hidden_fields"] = [
                f for f in context["panel_fields"] if f.is_hidden
            ]
            context["panel_fields"] = [
                f for f in context["panel_fields"] if not f.is_hidden
            ]
        return context

    def get_active_filters(self, filterset):
        """Leave the hidden ``sort`` field, the table's own ordering, out of the count."""
        active = super().get_active_filters(filterset)
        active.pop("sort", None)
        return active


class ItemCreateView(PermissionRequiredMixin, MVPCreateView):
    """Enter a reference by hand (FS-008, #74).

    The reference's contributors and identifiers are created in the same
    transaction as the reference itself through ``inlines``.
    """

    model = Item
    form_class = ItemForm
    template_name = "literature/ui/item_form.html"
    inlines = ITEM_INLINES
    permission_required = ADD_PERMISSION

    # No success_url: a saved reference lands on Item.get_absolute_url().
    show_list_action = True
    show_detail_action = True
    crud_views = CRUD_VIEWS

    # Otherwise the breadcrumb falls back to the model's verbose_name_plural ("Items").
    list_view_title = CATALOGUE_TITLE

    page_title = _("Add %(verbose_name)s")
    success_message = _("%(verbose_name)s added to the catalogue.")

    def get_context_data(self, **kwargs):
        """Add the field-group and contributor-datalist context the write form needs."""
        context = super().get_context_data(**kwargs)
        context.update(field_group_context(context["form"], context["inlines"]))
        context.update(contributor_datalist_context())
        context["cancel_url"] = reverse("literature:item-list")
        return context


#: The session keys carrying a staged file's identity from preview to confirm. They
#: never reach the page, so a request can only confirm what its own session staged.
IMPORT_TOKEN_SESSION_KEY = "literature_import_token"  # noqa: S105 — a session key name, not a secret
IMPORT_FORMAT_SESSION_KEY = "literature_import_format"

#: Which preview a confirmation is confirming; previewing again supersedes it. Unlike
#: the token this is safe to render, as alone it authorises nothing.
IMPORT_PREVIEW_SESSION_KEY = "literature_import_preview"


class ItemImportView(PermissionRequiredMixin, MVPFormView):
    """Choose a format and a file (FS-011, #103).

    ``model = Item`` although the form is not a ``ModelForm``: ``MVPFormView``
    raises ``ImproperlyConfigured`` with no model, and the breadcrumb belongs
    under the catalogue.
    """

    model = Item
    form_class = ImportForm
    template_name = "literature/ui/import_form.html"
    permission_required = ADD_PERMISSION
    list_view_title = CATALOGUE_TITLE
    show_list_action = True
    crud_views = CRUD_VIEWS
    page_title = _("Import references")

    def dispatch(self, request, *args, **kwargs):
        """Sweep abandoned stagings before every entry to this view."""
        StagedUpload().sweep()
        return super().dispatch(request, *args, **kwargs)

    def discard_staging(self):
        """Drop whatever this session had staged, and return the staging.

        Both submission paths supersede an earlier preview, which this session
        can no longer reach, so nothing should hold its file any longer.

        Returns:
            The ``StagedUpload`` used, ready to stage the next file.
        """
        staging = StagedUpload()
        superseded = self.request.session.get(IMPORT_TOKEN_SESSION_KEY)
        if superseded:
            staging.discard(superseded)
        for key in (
            IMPORT_TOKEN_SESSION_KEY,
            IMPORT_FORMAT_SESSION_KEY,
            IMPORT_PREVIEW_SESSION_KEY,
        ):
            self.request.session.pop(key, None)
        return staging

    def form_valid(self, form):
        """Import directly if previewing is skipped, else stage the file to preview."""
        format_name = form.cleaned_data["format"]
        format_class = get_format(format_name)

        if form.cleaned_data["skip_preview"]:
            # Otherwise an earlier preview would stay confirmable.
            self.discard_staging()
            result = format_class().import_file(form.cleaned_data["file"])
            context = self.get_context_data(form=form)
            report = ImportReport(result)
            context["report"] = report
            context["table"] = ImportReportTable(report.rows)
            # Rendered directly, not redirected to, so the reader sees the report.
            return render(self.request, "literature/ui/import_report.html", context)

        staging = self.discard_staging()

        token = staging.save(form.cleaned_data["file"])
        preview_id = get_random_string(22)
        self.request.session[IMPORT_TOKEN_SESSION_KEY] = token
        self.request.session[IMPORT_FORMAT_SESSION_KEY] = format_name
        self.request.session[IMPORT_PREVIEW_SESSION_KEY] = preview_id
        return redirect("literature:item-import-preview")


class ItemImportPreviewView(PermissionRequiredMixin, MVPFormView):
    """Rebuild the preview from the staged file on every GET (FS-011, #103).

    A dry run, not a stored result: reloading re-reads the staged file and
    changes nothing. ``form_class`` is set only because ``MVPFormView`` wants
    one; the confirm control's hidden field is built from the session.
    """

    model = Item
    form_class = ConfirmImportForm
    template_name = "literature/ui/import_preview.html"
    permission_required = ADD_PERMISSION
    list_view_title = CATALOGUE_TITLE
    show_list_action = True
    crud_views = CRUD_VIEWS
    page_title = _("Preview import")
    page_subtitle = _(
        "What importing this file would do. Nothing has been imported yet."
    )
    # Read-only: a POST would otherwise fail on the missing success address with a server error.
    http_method_names = ["get", "head", "options"]

    def get(self, request, *args, **kwargs):
        """Re-run the dry run against the staged file and render its report."""
        context = self.get_context_data()
        token = request.session.get(IMPORT_TOKEN_SESSION_KEY)
        format_name = request.session.get(IMPORT_FORMAT_SESSION_KEY)
        staging = StagedUpload()
        handle = staging.open(token) if token else None

        if handle is None:
            # A direct visit, a restarted or confirmed session, or a swept file.
            context["nothing_staged"] = True
            return self.render_to_response(context)

        with handle:
            result = get_format(format_name)().import_file(handle, dry_run=True)

        report = ImportReport(result)
        context["report"] = report
        # The outcome filter narrows rows client-side, so each carries its outcome as an Alpine expression.
        context["table"] = ImportReportTable(
            report.rows,
            row_attrs={
                "x-show": lambda record: (
                    f"outcome === 'all' || outcome === '{record.outcome.value}'"
                )
            },
        )
        # The tone is the outcome badge's own, so the control and the badge match.
        context["outcome_choices"] = [
            (outcome.value, outcome.label, OutcomeColumn.VARIANTS[outcome])
            for outcome in Outcome
        ]
        preview_id = request.session.get(IMPORT_PREVIEW_SESSION_KEY)
        context["confirm_form"] = ConfirmImportForm(initial={"preview": preview_id})
        return self.render_to_response(context)


class ItemImportRestartView(PermissionRequiredMixin, View):
    """Discard the staged file and return to an empty import form (FS-011, #103)."""

    permission_required = ADD_PERMISSION

    def post(self, request, *args, **kwargs):
        """Discard the session's staged file and redirect to a fresh import form."""
        token = request.session.pop(IMPORT_TOKEN_SESSION_KEY, None)
        request.session.pop(IMPORT_FORMAT_SESSION_KEY, None)
        request.session.pop(IMPORT_PREVIEW_SESSION_KEY, None)
        if token:
            StagedUpload().discard(token)
        return redirect("literature:item-import")


class ItemImportConfirmView(PermissionRequiredMixin, View):
    """Carry out the import a preview described, then return to the catalogue.

    FS-011, #103. The staged file's token and format come from the reader's own
    session, never from the page. Every outcome, including one with nothing to
    confirm, returns to the catalogue through the messages framework.
    """

    permission_required = ADD_PERMISSION

    def get(self, request, *args, **kwargs):
        """Refuse a bare GET; confirming is a POST-only action."""
        return redirect("literature:item-import")

    def post(self, request, *args, **kwargs):
        """Import the staged file if this session's preview matches, else refuse."""
        form = ConfirmImportForm(request.POST)
        form.is_valid()
        submitted_preview = form.cleaned_data.get("preview", "")

        expected = request.session.get(IMPORT_PREVIEW_SESSION_KEY)
        if not expected or submitted_preview != expected:
            # A stale tab: leave the session's current preview in place.
            messages.warning(
                request,
                _(
                    "There was nothing to confirm. The staged file is no longer available."
                ),
            )
            return redirect("literature:item-list")

        token = request.session.pop(IMPORT_TOKEN_SESSION_KEY, None)
        format_name = request.session.pop(IMPORT_FORMAT_SESSION_KEY, None)
        request.session.pop(IMPORT_PREVIEW_SESSION_KEY, None)

        staging = StagedUpload()
        handle = staging.open(token) if token else None

        if handle is None:
            # Nothing staged, or already confirmed or swept.
            messages.warning(
                request,
                _(
                    "There was nothing to confirm. The staged file is no longer available."
                ),
            )
            return redirect("literature:item-list")

        with handle:
            result = get_format(format_name)().import_file(handle)
        staging.discard(token)

        report = ImportReport(result)
        messages.success(
            request,
            _("%(created)d created, %(skipped)d skipped, %(failed)d failed.")
            % {
                "created": report.created,
                "skipped": report.skipped,
                "failed": report.failed,
            },
        )
        return redirect("literature:item-list")


class ItemUpdateView(PermissionRequiredMixin, MVPUpdateView):
    """Correct a reference that is wrong (FS-008, #74).

    The reference's contributors and identifiers are saved in the same
    transaction as the reference itself through ``inlines``.
    """

    model = Item
    form_class = ItemForm
    template_name = "literature/ui/item_form.html"
    inlines = ITEM_INLINES
    permission_required = CHANGE_PERMISSION

    show_list_action = True
    show_detail_action = True
    crud_views = CRUD_VIEWS

    page_title = _("Edit %(verbose_name)s")
    success_message = _("%(verbose_name)s updated.")

    def get_context_data(self, **kwargs):
        """Add the same context as create, plus this page's forced-visible groups."""
        context = super().get_context_data(**kwargs)
        context.update(
            field_group_context(
                context["form"],
                context["inlines"],
                FieldGroups.groups_holding_values(self.object),
            )
        )
        context.update(contributor_datalist_context())
        context["cancel_url"] = self.object.get_absolute_url()
        return context


class ItemDetailView(MVPDetailView):
    """The reference page (FS-006, #55)."""

    model = Item
    template_name = "literature/ui/item_detail.html"
    page_width = PageWidth.MEDIUM

    list_view_title = CATALOGUE_TITLE

    # Without this the breadcrumb's list link has no href.
    show_list_action = True

    directory: list[str] = ["update", "delete"]
    show_update_action = HasPermission(CHANGE_PERMISSION)
    show_delete_action = HasPermission(DELETE_PERMISSION)

    crud_views = CRUD_VIEWS

    def get_queryset(self):
        """Prefetch the related rows the page renders."""
        return (
            super()
            .get_queryset()
            .prefetch_related("item_names__name", "item_dates", "item_identifiers")
        )

    def get_page_title(self):
        """Title the page with the full title; ``str()`` cuts it at 80 characters."""
        return self.object.title or self.object.citation_key

    def get_context_data(self, **kwargs):
        """Add field sections, grouped contributors and linkable identifiers."""
        context = super().get_context_data(**kwargs)
        item = self.object
        context["field_sections"] = field_sections(item)
        context["year"] = item.year

        groups = contributor_groups(item)
        context["byline"] = groups[0] if groups else None
        context["other_contributors"] = groups[1:]

        numbering = []
        if item.volume:
            numbering.append(_("vol. %(volume)s") % {"volume": item.volume})
        if item.issue:
            numbering.append(_("no. %(issue)s") % {"issue": item.issue})
        if item.page:
            numbering.append(_("pp. %(page)s") % {"page": item.page})
        context["numbering"] = ", ".join(str(part) for part in numbering)
        context["publisher"] = ", ".join(
            value for value in (item.publisher, item.publisher_place) if value
        )

        # Decided here against a scheme allowlist: a template can only test that a value
        # looks like a URL, and ``javascript://x`` passes.
        identifiers = list(item.item_identifiers.all())
        for identifier in identifiers:
            identifier.href = web_url(identifier.value)
            if identifier.href is None and identifier.type == "DOI":
                identifier.href = doi_url(identifier.value)
        context["identifiers"] = identifiers
        return context


class ItemDeleteView(PermissionRequiredMixin, MVPDeleteView):
    """Remove a reference that does not belong (FS-008, #74)."""

    model = Item

    # Lists the cascading ItemName, ItemDate and ItemIdentifier rows before the reader commits.
    show_related_objects = True
    permission_required = DELETE_PERMISSION

    # The "list" and "detail" shorthands only resolve with their show_*_action flags set.
    success_url = "list"
    show_list_action = True
    show_detail_action = True
    crud_views = CRUD_VIEWS

    page_title = _("Delete %(verbose_name)s")
    success_message = _("%(verbose_name)s deleted.")

    def get_back_url(self) -> str:
        """Decline and land back on the reference, not the catalogue."""
        # The reference page's delete link carries no ?back, so the base fallback would
        # strand a decline on the catalogue. The explicit annotations below keep
        # mypy's warn_return_any quiet: MVPDeleteView ships no py.typed.
        candidate: str | None = self.request.GET.get("back")
        if candidate and url_has_allowed_host_and_scheme(
            url=candidate,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        ):
            return candidate
        detail_url: str | None = self.resolve_crud_url("detail")
        fallback: str = super().get_back_url()
        return detail_url or fallback


class ContributorDetailView(CatalogueListMixin, MVPListView):
    """The contributor page (FS-006, #55).

    A contributor's page is the catalogue filtered to what they are credited on,
    so it composes ``CatalogueListMixin``. It declares no filterset, so it has no
    search box or filter.
    """

    empty_state_heading = _("Not credited on anything yet")
    empty_state_message = _(
        "This contributor has no credited references in the catalogue."
    )

    @cached_property
    def contributor(self):
        """Return the contributor, resolved once per request before the queryset is built."""
        return get_object_or_404(Name, pk=self.kwargs["pk"])

    def get_queryset(self):
        """Filter the catalogue to items crediting this contributor, deduplicated."""
        # distinct(): a contributor with two roles on one item has two ItemName rows.
        return (
            super().get_queryset().filter(item_names__name=self.contributor).distinct()
        )

    def get_page_title(self):
        """Title the page with the contributor's own name, unsplit."""
        return str(self.contributor)

    def get_breadcrumbs(self):
        """Link back to the catalogue, then name this contributor."""
        return [
            {"text": CATALOGUE_TITLE, "href": reverse("literature:item-list")},
            {"text": self.get_page_title()},
        ]


class ReferenceAutocompleteView(AutocompleteModelView):
    """Answer a reference picker's search with the references that match.

    Matches the text against title, citation key, a contributor's family or
    literal name and a DOI, ranking a title or citation key that starts with
    the text first. Each result carries the reference's ``id`` and its
    ``label``.

    The route is open to everyone, as the catalogue list is
    (docs/adr/0022-the-front-ends-pages-are-open.md).
    """

    model = Item
    page_size = SEARCH_LIMIT
    value_fields = ["label"]
    virtual_fields = ["label"]
    allow_anonymous = True
    skip_authorization = True

    def setup(self, request, *args, **kwargs):
        """Cut the text to ``SEARCH_TEXT_LIMIT`` and hold the page to ``SEARCH_LIMIT``."""
        super().setup(request, *args, **kwargs)
        self.query = self.query.strip()[:SEARCH_TEXT_LIMIT]
        self.page_size = SEARCH_LIMIT

    def get(self, request, *args, **kwargs):
        """Refuse a NUL character before any query."""
        if "\x00" in self.query:
            return JsonResponse({"results": []}, status=400)
        return super().get(request, *args, **kwargs)

    def search(self, queryset, query):
        """Keep the references the catalogue's own search finds, and rank them."""
        # The search is ItemFilterSet's, so picker and catalogue agree on what a text finds
        # (docs/adr/0025-one-definition-of-what-the-catalogue-narrows-by.md).
        if not query:
            return queryset
        return (
            ItemFilterSet.base_filters["q"]
            .filter(queryset, query)
            .annotate(
                rank=Case(
                    When(
                        Q(title__istartswith=query)
                        | Q(citation_key__istartswith=query),
                        then=Value(0),
                    ),
                    default=Value(1),
                    output_field=IntegerField(),
                )
            )
        )

    def order_queryset(self, queryset):
        """Put a title or citation key that starts with the text first, then by title."""
        if self.query:
            return queryset.order_by("rank", "title", "pk")
        return queryset.order_by("title", "pk")

    @staticmethod
    def prepare_label(item):
        """Label a reference chosen in a field the way a search result is labelled."""
        return item_label(item)

    def hook_prepare_results(self, results):
        """Label each result, reading the page's references once."""
        items = Item.objects.prefetch_related("item_dates", "item_names__name").in_bulk(
            [result["id"] for result in results]
        )
        return [
            {"id": result["id"], "label": self.prepare_label(items[result["id"]])}
            for result in results
        ]
