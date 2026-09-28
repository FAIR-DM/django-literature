"""Views for the opt-in front end."""

import json
from collections import defaultdict
from functools import cached_property

from django.contrib import messages
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views import View
from django_filters.views import FilterView
from mvp.integrations.django_filters.views import MVPFilteredListView
from mvp.integrations.django_tables.views import MVPTableViewMixin
from mvp.views import (
    MVPDeleteView,
    MVPDetailView,
    MVPFormView,
    MVPInlineCreateView,
    MVPInlineUpdateView,
    MVPListView,
)

from literature.choices import ItemType, NameRole
from literature.importers import get_format
from literature.importers.results import Outcome
from literature.models import Item, ItemName, Name
from literature.ui.contributors import contributor_groups, stored_contributor_names
from literature.ui.fieldgroups import FieldGroups
from literature.ui.fields import scalar_fields
from literature.ui.filters import SEARCH_FIELDS, ItemFilterSet, get_active_filters
from literature.ui.forms import (
    CONTRIBUTOR_NAMES_DATALIST_ID,
    ConfirmImportForm,
    ImportForm,
    ItemForm,
)
from literature.ui.importing import ImportReport
from literature.ui.inlines import ContributorInline, DateInline, IdentifierInline
from literature.ui.links import web_url
from literature.ui.staging import StagedUpload
from literature.ui.tables import ImportReportTable, ItemTable, OutcomeColumn

#: The three related-row sets composed on both the create and update pages.
#: Declared once here so the two views and the page's own template use the
#: same list rather than three independent ones getting out of step.
ITEM_INLINES = [ContributorInline, DateInline, IdentifierInline]

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


def field_group_context(form, forced_groups=frozenset()):
    """Build the write form's template context for group-by-group rendering.

    The ``type`` field is pulled out of ``core`` and returned on its own: with
    no item type chosen, nothing else on the page is guarded to show, so it is
    the one control that has to render unconditionally. Every other group
    becomes a ``{key, label, fields}`` dict in a fixed order — a Django
    template cannot index a dict by its own loop variable, so the field list
    per group is resolved here rather than in ``item_form.html``.

    ``forced_groups`` is the forced-visible set — group names already
    holding a value on the object being edited, regardless of whether the
    current item type would otherwise show them
    (``FieldGroups.groups_holding_values``). The create view has none yet,
    so its default is empty; ``item_form.html`` reads the key as
    ``forced_groups_json`` and falls back to ``[]`` when it is absent.
    """
    groups = []
    for group, field_names in FieldGroups.GROUPS.items():
        names = [name for name in field_names if name != "type"]
        if not names:
            continue
        groups.append(
            {
                "key": group,
                "label": FieldGroups.GROUP_LABELS[group],
                "fields": [form[name] for name in names],
            }
        )
    return {
        "type_field": form["type"],
        "field_groups": groups,
        "type_groups_json": TYPE_GROUPS_JSON,
        "forced_groups_json": json.dumps(sorted(forced_groups)),
    }


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
    the contributor page a search box and filters it must not have, and
    overriding ``filterset_class`` back to unset does not disable filtering —
    it 500s instead, since ``FilterMixin.get_filterset_class()`` falls
    through to a filterset generated over every field of ``Item``, including
    its two ``JSONField``s, which django-filter has no filter for.
    """

    model = Item
    page_title = CATALOGUE_TITLE
    # No ``template_name``: the page renders through django-mvp's own
    # ``list_view.html``, which reaches the shell through the default
    # ``base.html`` django-mvp has shipped since 0.18 — this app carried a
    # pass-through of its own until then. Only the card is ours.
    #
    # ``ItemListView``'s own default — ``ContributorDetailView`` overrides
    # it back to its own template, the same as it does today.
    list_item_template = "literature/ui/item_list_item.html"

    # "create" alone in directory shows nothing without the matching
    # show_create_action flag — CRUDDirectoryMixin defaults every
    # show_<action>_action to False and drops the entry silently.
    # create_form_class stays unset: a thirteen-group form does not belong in
    # the list component's modal, so it renders a plain link instead.
    directory: list[str] = ["create"]
    show_create_action = True
    crud_views = CRUD_VIEWS

    def get_queryset(self):
        """Prefetch what a row needs so a page costs a constant number of queries."""
        return super().get_queryset().prefetch_related("item_names__name", "item_dates")

    def get_model_info(self):
        """Name the collection ``CATALOGUE_NAME_PLURAL``, not the model's own name."""
        return {
            **super().get_model_info(),
            "verbose_name_plural": CATALOGUE_NAME_PLURAL,
        }

    def get_context_data(self, **kwargs):
        """Group each row's contributors by role, from the queryset's prefetch."""
        context = super().get_context_data(**kwargs)
        for page_item in context["object_list"]:
            page_item.contributor_groups = contributor_groups(page_item)
        return context


class ItemListView(CatalogueListMixin, MVPFilteredListView):
    """The catalogue list (FS-006, #55)."""

    # Mandatory, not inherited: MVPFilteredListView sets no paginate_by at
    # all (unlike MVPListView, this view's own base until now), and without
    # one pagination switches off entirely. 24 is this view's own
    # already-established page size, kept so the change of base class does
    # not also change how much is on a page — same reasoning as
    # ItemTableView's own paginate_by below.
    paginate_by = 24

    search_fields = SEARCH_FIELDS
    filterset_class = ItemFilterSet

    empty_state_heading = _("Nothing in the catalogue yet")
    empty_state_message = _("References imported or created will appear here.")

    # A wrapper template carries the action row, overriding list_view.html's
    # page.actions block. Set here, not on CatalogueListMixin — the
    # contributor page composes that mixin too and must not gain either.
    template_name = "literature/ui/item_list_page.html"
    directory: list[str] = ["create", "import"]
    show_import_action = True
    list_actions: list[str] = ["search", "sort", "filter", "create", "import"]

    def get_url_kwargs(self, action):
        """Resolve "import" as collection-level, like the "list"/"create" default."""
        # Without this, a list view's always-empty self.kwargs makes
        # directory.import_url never resolve. ItemTableView carries the
        # same override; edit the two together.
        if action == "import":
            return {}
        return super().get_url_kwargs(action)

    def get_context_data(self, **kwargs):
        """Recompute applied-filter count excluding the hidden "sort" field."""
        context = super().get_context_data(**kwargs)
        # MVPFilteredListView's own count treats "sort" as an applied filter,
        # which it is not. ItemTableView.get_context_data() below calls the
        # same exclusion.
        if context.get("filter"):
            active = get_active_filters(self.filterset)
            context["applied_filters"] = active
            context["applied_filter_count"] = len(active)

        context["list_actions"] = self.list_actions
        return context


class ItemTableView(MVPTableViewMixin, FilterView):
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

    # Mandatory, not inherited: MVPTableView sets no paginate_by at all, and
    # without one the whole footer bar disappears (it renders under
    # `{% if page_obj %}`). 24 matches the card list's own page size.
    paginate_by = 24

    page_title = CATALOGUE_TITLE

    # The table page has no actions hook of its own, so a wrapper template
    # overrides table_view.html's own page.actions block (not
    # list_view.html's, which renders no table).
    #
    # django-mvp 0.19.2 dropped its own MVPTableViewMixin.actions hook
    # (upstream commit dfa7c3a), leaving <c-page.list.actions />'s c-vars
    # default in force regardless of what a project declares. table_actions
    # restores the hook under its own name.
    #
    # Not named "actions": a Cotton slot falls through to a context variable
    # of the same name when unfilled, so a key called `actions` would print
    # its repr into every toolbar's `actions` slot on the page.
    template_name = "literature/ui/item_table_page.html"
    table_actions: list[str] = ["search", "filter", "create", "import"]
    directory: list[str] = ["create", "import"]
    show_create_action = True
    show_import_action = True
    crud_views = CRUD_VIEWS
    search_fields = SEARCH_FIELDS
    filterset_class = ItemFilterSet

    # Same flag name and semantics as ItemDetailView.show_update_action — a
    # project that overrides one to gate the write page overrides the other
    # the same way to gate this row control.
    show_update_action = True

    def get_url_kwargs(self, action):
        """Resolve "import" as collection-level, like the "list"/"create" default."""
        # Same reasoning as ItemListView.get_url_kwargs(); edit the two together.
        if action == "import":
            return {}
        return super().get_url_kwargs(action)

    # No order_by: MVPTableViewMixin raises ImproperlyConfigured at
    # instantiation if it finds one — ordering lives on the table class.

    empty_state_heading = _("Nothing in the catalogue yet")
    empty_state_message = _("References imported or created will appear here.")

    # A search or filter matching nothing reads differently from a
    # genuinely empty catalogue, and keeps its controls — django-mvp's own
    # empty state otherwise renders the same "nothing here" copy either way.
    no_matches_heading = _("No references match your search")
    no_matches_message = _(
        "Try a different search term, or clear the search and filters."
    )

    def get_empty_state_heading(self):
        """Show the no-matches heading instead when the catalogue is narrowed."""
        if self.catalogue_is_narrowed():
            return self.no_matches_heading
        return super().get_empty_state_heading()

    def get_empty_state_message(self):
        """Show the no-matches message instead when the catalogue is narrowed."""
        if self.catalogue_is_narrowed():
            return self.no_matches_message
        return super().get_empty_state_message()

    def catalogue_is_narrowed(self):
        """Whether the current request carries a search term or a filter value.

        Read from the raw request rather than from ``self.filterset.qs``
        being empty — an empty catalogue with no query in force is a
        different circumstance from a query that matched nothing, and both
        can leave the same queryset empty. ``self.filterset`` is already
        built and bound by the time a view method reaches here.
        """
        if self.request.GET.get("q", "").strip():
            return True
        return any(
            self.request.GET.get(name, "").strip() for name in self.filterset.filters
        )

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

    def get_filterset_kwargs(self, filterset_class):
        """Keep the filterset always bound, even on a bare, param-less request."""
        # FilterMixin's default binds with `self.request.GET or None`, and an
        # empty QueryDict is falsy, leaving the filterset unbound. A
        # QueryDict is `is not None` even when empty, so this fixes it.
        kwargs = super().get_filterset_kwargs(filterset_class)
        kwargs["data"] = self.request.GET
        return kwargs

    def get_context_data(self, **kwargs):
        """Add applied_filters/applied_filter_count, which no base here supplies."""
        # This view composes MVPTableViewMixin, FilterView directly rather
        # than through MVPFilteredListView, so its badge-count logic never
        # runs here. Mirrored rather than reached through a third mixin:
        # multiple inheritance from both bases would fight over
        # get_queryset()/get_context_data() for no benefit.
        context = super().get_context_data(**kwargs)
        if context.get("filter") and hasattr(self.filterset.form, "cleaned_data"):
            # get_active_filters() excludes "sort" — the table's own
            # ordering, carried as a hidden filter field — from the count.
            # ItemListView.get_context_data() calls the same function.
            active = get_active_filters(self.filterset)
            context["applied_filters"] = active
            context["applied_filter_count"] = len(active)

        context["table_actions"] = self.table_actions
        return context

    def get_model_info(self):
        """Name the collection ``CATALOGUE_NAME_PLURAL``, not the model's own name."""
        return {
            **super().get_model_info(),
            "verbose_name_plural": CATALOGUE_NAME_PLURAL,
        }

    def get_table_kwargs(self):
        """Pass show_action("update") directly; get_directory() is empty here."""
        return {
            **super().get_table_kwargs(),
            "show_update_action": self.show_action("update"),
        }


class ItemCreateView(MVPInlineCreateView):
    """Enter a reference by hand (FS-008, #74).

    Composes django-mvp's inline mixin so the reference's contributors,
    dates and identifiers are created in the same transaction as the
    reference itself — no save path of its own.
    """

    model = Item
    form_class = ItemForm
    template_name = "literature/ui/item_form.html"
    inlines = ITEM_INLINES

    # Item has no get_absolute_url(), so success_url is mandatory. The
    # "detail" shorthand only resolves once show_detail_action is set, or
    # get_success_url() falls through to the literal path "detail" and 404s.
    success_url = "detail"
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
        context.update(field_group_context(context["form"]))
        context.update(contributor_datalist_context())
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


class ItemImportView(MVPFormView):
    """Choose a format and a file (FS-011, #103).

    ``model = Item`` even though the form below is not a ``ModelForm``:
    ``MVPFormView``'s context machinery raises ``ImproperlyConfigured`` on
    first render with no model at all, and the page's breadcrumb genuinely
    belongs under the catalogue.
    """

    model = Item
    form_class = ImportForm
    template_name = "literature/ui/import_form.html"
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


class ItemImportPreviewView(MVPFormView):
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


class ItemImportRestartView(View):
    """Discard the staged file and return to an empty import form (FS-011, #103)."""

    def post(self, request, *args, **kwargs):
        """Discard the session's staged file and redirect to a fresh import form."""
        token = request.session.pop(IMPORT_TOKEN_SESSION_KEY, None)
        request.session.pop(IMPORT_FORMAT_SESSION_KEY, None)
        request.session.pop(IMPORT_PREVIEW_SESSION_KEY, None)
        if token:
            StagedUpload().discard(token)
        return redirect("literature:item-import")


class ItemImportConfirmView(View):
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


class ItemUpdateView(MVPInlineUpdateView):
    """Correct a reference that is wrong (FS-008, #74).

    Composes django-mvp's inline mixin so the reference's contributors,
    dates and identifiers are saved in the same transaction as the
    reference itself — no save path of its own.
    """

    model = Item
    form_class = ItemForm
    template_name = "literature/ui/item_form.html"
    inlines = ITEM_INLINES

    # Same shorthand and reasoning as ItemCreateView: Item has no
    # get_absolute_url(), so success_url is mandatory, and the "detail"
    # shorthand only resolves once show_detail_action is set.
    success_url = "detail"
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
                context["form"], FieldGroups.groups_holding_values(self.object)
            )
        )
        context.update(contributor_datalist_context())
        return context


class ItemDetailView(MVPDetailView):
    """The reference page (FS-006, #55)."""

    model = Item
    template_name = "literature/ui/item_detail.html"

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
    show_update_action = True
    show_delete_action = True

    crud_views = CRUD_VIEWS

    def get_queryset(self):
        """Prefetch the related rows the page renders."""
        return (
            super()
            .get_queryset()
            .prefetch_related("item_names__name", "item_dates", "item_identifiers")
        )

    def get_context_data(self, **kwargs):
        """Add scalar fields, grouped contributors and linkable identifiers."""
        context = super().get_context_data(**kwargs)
        context["scalar_fields"] = list(scalar_fields(self.object))
        context["contributor_groups"] = contributor_groups(self.object)

        # Whether an identifier may be rendered as a link is decided here,
        # against a scheme allowlist, never in the template: a template can
        # only ask whether the value *looks* like a URL, and
        # ``javascript://x`` passes that test.
        identifiers = list(self.object.item_identifiers.all())
        for identifier in identifiers:
            identifier.href = web_url(identifier.value)
        context["identifiers"] = identifiers
        return context


class ItemDeleteView(MVPDeleteView):
    """Remove a reference that does not belong (FS-008, #74)."""

    model = Item

    # Lists what cascades (ItemName/ItemDate/ItemIdentifier rows) before the
    # reader commits. Name records are never listed: nothing points from
    # Item to Name directly, only ItemName rows do.
    show_related_objects = True

    # Item has no get_absolute_url(), so success_url is mandatory; the
    # "list" shorthand only resolves once show_list_action is set.
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
    out-of-range page all arrive with ``MVPListView``. Plain, not
    ``MVPFilteredListView``: this page carries no search box and no filter —
    ``ItemListView`` is the only concrete view that composes the mixin with a
    filtered base. The contributor is the page's subject, not the object it
    lists, which is the only thing here the base class does not already know.
    """

    list_item_template = "literature/ui/contributor_item.html"

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

    def get_context_data(self, **kwargs):
        """Annotate each page item with the role(s) this contributor held on it."""
        context = super().get_context_data(**kwargs)

        # list() forces the page's queryset now, caching it in place, so the
        # annotation below costs no extra query.
        items_on_page = list(context["object_list"])

        # The role(s) *this* contributor held on each item, from a single
        # further query — not one per row.
        roles_by_item = defaultdict(list)
        for item_name in ItemName.objects.filter(
            name=self.contributor, item__in=items_on_page
        ):
            roles_by_item[item_name.item_id].append(item_name.get_role_display())
        for page_item in items_on_page:
            page_item.credited_roles = roles_by_item[page_item.id]

        return context
