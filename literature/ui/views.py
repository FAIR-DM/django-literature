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

#: The three related-row sets composed on both the create and update pages.
#: Declared once here so the two views and the page's own template use the
#: same list rather than three independent ones getting out of step.
ITEM_INLINES = [*CONTRIBUTOR_INLINES, IdentifierInline]

#: What the catalogue calls itself, everywhere a reader is shown its name.
#: "Item" is the model's name and reads as the store's vocabulary rather than
#: the reader's, but renaming the model would also rename it in the admin and
#: the migration state, so the name is set here instead.
CATALOGUE_TITLE = _("Publications")

#: The same word used mid-sentence, as its own message rather than
#: ``CATALOGUE_TITLE.lower()``: lowercasing is an English habit and a
#: language that capitalises its nouns would be served the wrong form.
CATALOGUE_NAME_PLURAL = _("publications")

#: One shared CRUD-action to namespaced-URL-name map for every view in this
#: app. Under this app's ``app_name = "literature"``, a bare
#: ``reverse("item-list")`` raises ``NoReverseMatch``, so every view carries
#: this dict rather than a partial per-view override.
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
    """

    def __init__(self, permission):
        self.permission = permission

    def __call__(self, user):
        """Return whether *user* holds the permission."""
        return user.has_perm(self.permission)


#: Every ``ItemType`` value mapped to the group names its form shows by
#: default, serialised once into every write page. Built at import time: the
#: mapping is a module-level constant (``literature/ui/fieldgroups.py``), so
#: there is nothing request-specific to recompute.
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

    ``forced_groups`` is the set of groups already holding a value on the
    object being edited (``FieldGroups.groups_holding_values``), shown whatever
    the item type. A group holding a field with an error joins it, so an error
    is never drawn inside a section the page has hidden.
    """
    with_errors = {
        group
        for group, names in FieldGroups.GROUPS.items()
        if any(name in form.errors for name in names)
    }
    *contributor_sets, identifier_set = inlines
    # The identifier set fills a tab of its own, whose label already names
    # it, so it draws no heading of its own.
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
    """Every error on the page, in page order, each with the id of the field to fix.

    Drawn as one summary above the form, since an error may sit in a tab the
    person is not looking at.
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

    Shared by both write views rather than computed on a common base: the
    two do not otherwise share a base beyond django-mvp's inline mixin, and
    one dict built the same way both times is simpler than a mixin neither
    view needs for anything else.
    """
    return {
        "contributor_names_datalist_id": CONTRIBUTOR_NAMES_DATALIST_ID,
        "contributor_names": stored_contributor_names(),
    }


class CatalogueListMixin:
    """The card-list configuration ``ItemListView`` and ``ContributorDetailView`` share.

    No base class of its own: each of the two concrete views exists today and
    each composes this with its own base, so this is not a speculative base
    class under Article III. Subclassing ``ItemListView`` directly would hand
    the contributor page a search box and filters it must not have.
    """

    model = Item
    page_title = CATALOGUE_TITLE
    # No ``template_name``: the page renders through django-mvp's own
    # ``list_view.html``. Only the card is ours.
    #
    # The card is the reference component in a card, so the catalogue and a
    # project's own pages show a reference the same way.
    list_item_template = "literature/ui/item_list_item.html"

    # "create" alone in directory shows nothing without the matching
    # show_create_action flag — CRUDDirectoryMixin defaults every
    # show_<action>_action to False and drops the entry silently.
    # create_form_class stays unset: a thirteen-group form does not belong in
    # the list component's modal, so it renders a plain link instead.
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
    # The filters are a drawer at every width, opened from the toolbar's
    # Filters button, never a column beside the list.
    filter_panel_attrs = {"position": "end", "breakpoint": False}

    empty_state_heading = _("Nothing in the catalogue yet")
    empty_state_message = _("References imported or created will appear here.")

    directory: list[str] = ["create", "import"]
    show_import_action = HasPermission(ADD_PERMISSION)

    def get_url_kwargs(self, action):
        """Resolve "import" as collection-level, like the "list"/"create" default."""
        # Without this, a list view's always-empty self.kwargs makes
        # directory.import_url never resolve. ItemTableView carries the
        # same override; edit the two together.
        if action == "import":
            return {}
        return super().get_url_kwargs(action)


class ItemTableView(MVPTableView):
    """The catalogue as a table (FS-009, #87).

    ``ItemListView`` keeps its name, its card template and its behaviour
    unchanged; this is a new, sibling view, and ``urls.py`` points the
    ``item-list`` route at it. ``ContributorDetailView`` stays on cards
    through ``CatalogueListMixin``, the configuration it shares with
    ``ItemListView`` rather than an inheritance from it, so it is unaffected
    either way.
    """

    model = Item
    table_class = ItemTable

    # Without a page size the table renders every row and no pager.
    # 24 matches the card list's own page size.
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
    # The filters are a drawer at every width, opened from the toolbar's
    # Filters button, never a column beside the table.
    filter_panel_attrs = {"position": "end", "breakpoint": False}

    # No order_by: MVPTableViewMixin raises ImproperlyConfigured at
    # instantiation if it finds one — ordering lives on the table class.

    def get_url_kwargs(self, action):
        """Resolve "import" as collection-level, like the "list"/"create" default."""
        # Same reasoning as ItemListView.get_url_kwargs(); edit the two together.
        if action == "import":
            return {}
        return super().get_url_kwargs(action)

    empty_state_heading = _("Nothing in the catalogue yet")
    empty_state_message = _("References imported or created will appear here.")

    def get_queryset(self):
        """Prefetch what the credited-names and issued cells read."""
        # No "issued" annotation here: ItemFilterSet.filter_queryset()
        # (literature/ui/filters.py) already annotates it on every request,
        # so annotating it again would double-annotate the same alias.
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
        """Leave out empty choices, and draw the hidden ``sort`` field in the toolbar's form.

        Every visible filter is in the toolbar, so a panel holding only the
        hidden field would put a Filters button on the page that opens nothing.
        """
        context = super().get_context_data(**kwargs)
        # A choice the catalogue holds no values for, such as Language when
        # no reference records one, offers nothing to pick, so it is left out.
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

    The reference's contributors, dates and identifiers are created in the
    same transaction as the reference itself through ``inlines`` — no save
    path of its own.
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

    # The breadcrumb's own text — left unset, get_list_title() falls through
    # to the model's verbose_name_plural ("Items") instead.
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


#: The two session keys carrying a staged file's identity across the preview
#: to confirm round trip. Never in the page, never in ``ConfirmImportForm`` —
#: a request can only confirm what its own session staged, because this is
#: the only place the token is ever written down.
IMPORT_TOKEN_SESSION_KEY = "literature_import_token"  # noqa: S105 — a session key name, not a secret
IMPORT_FORMAT_SESSION_KEY = "literature_import_format"

#: Which preview a confirmation is confirming. A session stages one file at a
#: time, so previewing again supersedes whatever came before, and a
#: confirmation is carried out only where the page and the session agree.
#: Unlike the token this is safe to render: alone it authorises nothing.
IMPORT_PREVIEW_SESSION_KEY = "literature_import_preview"


class ItemImportView(PermissionRequiredMixin, MVPFormView):
    """Choose a format and a file (FS-011, #103).

    ``model = Item`` even though the form below is not a ``ModelForm``:
    ``MVPFormView``'s context machinery raises ``ImproperlyConfigured`` on
    first render with no model at all, and the page's breadcrumb genuinely
    belongs under the catalogue.
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

        Both submission paths supersede an earlier preview: this session can
        no longer reach it, so nothing should hold its file for the rest of
        the retention window.
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
            # Discarding here supersedes an earlier preview exactly as
            # previewing again would — otherwise it would still be reachable
            # and offering to confirm a second, unwanted import.
            self.discard_staging()
            result = format_class().import_file(form.cleaned_data["file"])
            context = self.get_context_data(form=form)
            report = ImportReport(result)
            context["report"] = report
            context["table"] = ImportReportTable(report.rows)
            # Rendered directly, never through get_success_url()/redirect:
            # the reader must have read the report before anything written
            # by it can be assumed.
            return render(self.request, "literature/ui/import_report.html", context)

        staging = self.discard_staging()

        token = staging.save(form.cleaned_data["file"])
        preview_id = get_random_string(22)
        self.request.session[IMPORT_TOKEN_SESSION_KEY] = token
        self.request.session[IMPORT_FORMAT_SESSION_KEY] = format_name
        self.request.session[IMPORT_PREVIEW_SESSION_KEY] = preview_id
        # Safe to redirect: the staged file, not anything carried in the
        # URL, is what ItemImportPreviewView's own GET re-reads.
        return redirect("literature:item-import-preview")


class ItemImportPreviewView(PermissionRequiredMixin, MVPFormView):
    """Rebuild the preview from the staged file on every GET (FS-011, #103).

    A dry run, not a stored result: reloading this address re-reads the same
    staged file and re-runs the same dry run, which reports the same outcomes
    and changes nothing. ``form_class`` is set for the same reason
    ``ItemImportView`` sets ``model`` — ``MVPFormView``'s context machinery
    wants one even though this view's own GET never binds it; the confirm
    control's hidden field is built separately, from the session.
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
    # This page reads; it never writes. Without this, the form base class
    # answers a POST by looking for a success address this view has no
    # reason to define, and the reader takes a server error, not a refusal.
    http_method_names = ["get", "head", "options"]

    def get(self, request, *args, **kwargs):
        """Re-run the dry run against the staged file and render its report."""
        context = self.get_context_data()
        token = request.session.get(IMPORT_TOKEN_SESSION_KEY)
        format_name = request.session.get(IMPORT_FORMAT_SESSION_KEY)
        staging = StagedUpload()
        handle = staging.open(token) if token else None

        if handle is None:
            # A direct visit, a restarted or already confirmed session, or
            # one swept in the meantime.
            context["nothing_staged"] = True
            return self.render_to_response(context)

        with handle:
            result = get_format(format_name)().import_file(handle, dry_run=True)

        report = ImportReport(result)
        context["report"] = report
        # The outcome filter narrows these rows client-side, so each one
        # carries its own outcome as an Alpine expression rather than the
        # view building a JSON payload for a request that never happens.
        context["table"] = ImportReportTable(
            report.rows,
            row_attrs={
                "x-show": lambda record: (
                    f"outcome === 'all' || outcome === '{record.outcome.value}'"
                )
            },
        )
        # Value, label and the tone that outcome's badge already uses, so the
        # control and the badge for one outcome read as the same thing and
        # restyling the badges moves the filter with them.
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

    FS-011, #103. ``ConfirmImportForm`` declares no field of consequence: the
    staged file's token and the format it was staged as both come from the
    reader's own session, never from this page. Nothing here renders a
    template of its own — every outcome, including one with nothing to
    confirm, is carried back to the catalogue through the messages framework
    the interface already renders. There is no success page of its own:
    every per-entry detail was already on the preview the reader just read,
    and the message here confirms that, not a second report.
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
            # A page describing a preview this session has since replaced.
            # Nothing is popped or discarded: a stale tab must not take the
            # reader's current preview away from them.
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
            # Nothing this session staged, or it has already been confirmed
            # or swept — either way there is nothing to import.
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

    The reference's contributors, dates and identifiers are saved in the
    same transaction as the reference itself through ``inlines`` — no save
    path of its own.
    """

    model = Item
    form_class = ItemForm
    template_name = "literature/ui/item_form.html"
    inlines = ITEM_INLINES
    permission_required = CHANGE_PERMISSION

    # No success_url: a saved reference lands on Item.get_absolute_url().
    show_list_action = True
    show_detail_action = True
    crud_views = CRUD_VIEWS

    page_title = _("Edit %(verbose_name)s")
    success_message = _("%(verbose_name)s updated.")

    def get_context_data(self, **kwargs):
        """Add the same context as create, plus this page's forced-visible groups."""
        context = super().get_context_data(**kwargs)
        # groups_holding_values(self.object) is the forced-visible set: a
        # group the stored type would not otherwise show still renders when
        # a value already lives in it.
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

    # The breadcrumb's own text, which otherwise derives from the model's
    # verbose_name_plural and would read "Items" beside a page titled
    # "Publications".
    list_view_title = CATALOGUE_TITLE

    # Reverses the breadcrumb's list link. The default False leaves it
    # href-less: PageObjectMixin.get_breadcrumbs() calls resolve_crud_url("list")
    # regardless, and show_list_action gates whether that call is even attempted.
    show_list_action = True

    # show_delete_action stayed unset until ItemDeleteView and its route
    # existed — turning it on earlier would have turned every reference-page
    # request into a NoReverseMatch.
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

        # The first role group is the byline under the title, normally the
        # authors. Any further roles (editors, translators) sit beside it.
        groups = contributor_groups(item)
        context["byline"] = groups[0] if groups else None
        context["other_contributors"] = groups[1:]

        # Where the work appeared, as one line: the container with its
        # volume, issue and pages, or the publisher with its place.
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

        # Whether an identifier may be rendered as a link is decided here,
        # against a scheme allowlist, never in the template: a template can
        # only ask whether the value *looks* like a URL, and
        # ``javascript://x`` passes that test.
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

    # Lists what cascades (ItemName/ItemDate/ItemIdentifier rows) before the
    # reader commits. Name records are never listed: nothing points from
    # Item to Name directly, only ItemName rows do.
    show_related_objects = True
    permission_required = DELETE_PERMISSION

    # The "list" shorthand only resolves once show_list_action is set.
    # show_detail_action is what get_back_url() below needs for "detail".
    success_url = "list"
    show_list_action = True
    show_detail_action = True
    crud_views = CRUD_VIEWS

    page_title = _("Delete %(verbose_name)s")
    success_message = _("%(verbose_name)s deleted.")

    def get_back_url(self) -> str:
        """Decline and land back on the reference, not the catalogue.

        ``MVPDeleteView.get_back_url()`` honours a validated ``?back`` from
        the query string and otherwise falls back to the catalogue list. The
        reference page's own delete link carries no ``?back`` (only the
        update page's does), so that fallback would strand a decline on the
        catalogue instead of the reference it was considering removing.
        Overridden to fall through to the ``detail`` shorthand instead — the
        object still exists at GET time, so its own URL is always resolvable.
        """
        # Explicit annotations, not just style: MVPDeleteView ships no
        # py.typed, so every attribute reached through it (self.request,
        # resolve_crud_url(), super().get_back_url()) resolves to Any —
        # mypy's warn_return_any would otherwise flag a plain "-> str" here.
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

    A contributor's page is the catalogue filtered to what they are credited
    on, so it *is* a list view: it composes ``CatalogueListMixin`` rather
    than reproducing the card list's configuration. Pagination, the page
    size, the empty state, the grid configuration and the not-found on an
    out-of-range page all arrive with ``MVPListView``. It declares no
    filterset, so this page carries no search box and no filter. The contributor is the page's subject, not the object it
    lists, which is the only thing here the base class does not already know.
    """

    empty_state_heading = _("Not credited on anything yet")
    empty_state_message = _(
        "This contributor has no credited references in the catalogue."
    )

    @cached_property
    def contributor(self):
        """Resolve the contributor once per request, before the queryset is built."""
        return get_object_or_404(Name, pk=self.kwargs["pk"])

    def get_queryset(self):
        """Filter the catalogue to items crediting this contributor, deduplicated."""
        # .distinct() is load-bearing: a contributor holding two roles on one
        # item has two ItemName rows, and without it the item would appear
        # twice.
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

    The route is open to everyone (ADR 0036): the catalogue list is, and this
    search follows its read rule.
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
        """Refuse a NUL character before any query.

        No text answers with the first page of the catalogue by title, which the
        picker loads as soon as it is opened.
        """
        if "\x00" in self.query:
            return JsonResponse({"results": []}, status=400)
        return super().get(request, *args, **kwargs)

    def search(self, queryset, query):
        """Keep the references the catalogue's own search finds, and rank them.

        The search is ``ItemFilterSet``'s, so the picker and the catalogue
        agree on what a text finds (ADR 0025). The field validates a
        submission against this view's queryset without any text, so no text
        leaves the queryset whole.
        """
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
        """Put a title or citation key that starts with the text first, then by title.

        With no text, order by title alone.
        """
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
