"""Views for the opt-in front end.

Filled in one class per story: ``ItemListView`` (US-1), ``ItemDetailView``
(US-2), ``ContributorDetailView`` (US-4), ``ItemCreateView`` (US-1 again),
``ItemUpdateView`` (US-2 again), ``ItemDeleteView`` (US-3).
"""

import json
from collections import defaultdict
from functools import cached_property

from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django_filters.views import FilterView
from mvp.integrations.django_filters.views import MVPFilteredListView
from mvp.integrations.django_tables.views import MVPTableViewMixin
from mvp.views import MVPCreateView, MVPDeleteView, MVPDetailView, MVPFormView, MVPListView, MVPUpdateView

from literature.choices import ItemType, NameRole
from literature.importers import get_format
from literature.models import Item, ItemName, Name
from literature.ui.contributors import contributor_groups
from literature.ui.fieldgroups import FieldGroups
from literature.ui.fields import scalar_fields
from literature.ui.filters import SEARCH_FIELDS, ItemFilterSet, get_active_filters
from literature.ui.forms import ConfirmImportForm, ImportForm, ItemForm
from literature.ui.importing import ImportReport
from literature.ui.links import web_url
from literature.ui.staging import StagedUpload
from literature.ui.tables import ImportReportTable, ItemTable

#: What the catalogue calls itself, everywhere a reader is shown its name — the
#: list page's own heading and the breadcrumb back to it from both other pages.
#: "Item" is the model's name and reads as the store's vocabulary rather than
#: the reader's, but renaming the model to fix one heading would rename it in
#: the admin and in the migration state too, so the name is set here instead.
CATALOGUE_TITLE = _("Publications")

#: The same word where the page uses it inside a sentence, as its own message
#: rather than ``CATALOGUE_TITLE.lower()``: lowercasing is an English habit and
#: a language that capitalises its nouns would be served the wrong form.
CATALOGUE_NAME_PLURAL = _("publications")

#: One shared CRUD-action → namespaced-URL-name map for every view in this
#: app (plan.md D-6). ``MVP_CONFIG["view_names"]``'s own default is
#: unnamespaced (``"item-list"``, not ``"literature:item-list"``), and under
#: this app's ``app_name = "literature"``, a bare ``reverse("item-list")``
#: raises ``NoReverseMatch``. One dict, assigned on every view that carries
#: it, is what makes "every name in every view's ``crud_views`` reverses" a
#: literally true statement rather than depending on which keys a partial
#: per-view override happened to name (DR-006).
#:
#: All five actions are registered in ``urls.py``. A view still only reaches
#: for the ones its own ``show_<action>_action`` flags switch on, so assigning
#: the whole map everywhere costs nothing and removes the partial-override
#: failure this dict exists to prevent.
CRUD_VIEWS = {
    "list": "literature:{model_name}-list",
    "detail": "literature:{model_name}-detail",
    "create": "literature:{model_name}-create",
    "update": "literature:{model_name}-update",
    "delete": "literature:{model_name}-delete",
    "import": "literature:{model_name}-import",
}

#: Every ``ItemType`` value mapped to the group names its form shows by
#: default, serialised once into every write page (plan.md D-3). Built at
#: import time, not per-request: the mapping is a module-level constant
#: (``literature/ui/fieldgroups.py``), so there is nothing request-specific
#: to recompute.
TYPE_GROUPS_JSON = json.dumps({item_type: sorted(FieldGroups.groups_for(item_type)) for item_type in ItemType.values})


def field_group_context(form, forced_groups=frozenset()):
    """The write form's template context for group-by-group rendering (D-3).

    The ``type`` field is pulled out of ``core`` and returned on its own: with
    no item type chosen, nothing else on the page is guarded to show (FR-002),
    so the type field is the one control that has to render unconditionally.
    Every other group becomes a ``{key, label, fields}`` dict in a fixed
    order — a Django template cannot index a dict by its own loop variable,
    so the field list per group is resolved here rather than in
    ``item_form.html``.

    ``forced_groups`` is the FR-010/FR-014 forced-visible set — group names
    already holding a value on the object being edited, regardless of
    whether the current item type would otherwise show them
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


class CatalogueListMixin:
    """The card-list configuration ``ItemListView`` and ``ContributorDetailView``
    share (plan.md D-6): no base class of its own — each of the two concrete
    views exists today and each composes this with its own base, so this is
    not a speculative base class under Article III.

    ``ItemListView`` becoming ``MVPFilteredListView`` (T022) is what forces
    the split: subclassing it would otherwise hand the contributor page a
    search box and four filters it must not have (FR-025). Extracting the
    two views' shared configuration here, rather than overriding it back off
    on a subclass, is the mechanism plan.md D-6 names — overriding
    ``filterset_class`` back to unset does not disable filtering and 500s
    the page instead (``FilterMixin.get_filterset_class()`` falls through to
    a filterset generated over every field of ``Item``, including its two
    ``JSONField``s, which django-filter has no filter for).
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
    # show_create_action flag (plan.md D-6) — CRUDDirectoryMixin defaults
    # every show_<action>_action to False and drops the entry silently.
    # create_form_class stays unset on purpose: a thirteen-group form does
    # not belong in the list component's modal (plan.md D-8), so the
    # component instead renders a plain link to the create page.
    directory: list[str] = ["create"]
    show_create_action = True
    crud_views = CRUD_VIEWS

    def get_queryset(self):
        # Keep the model's declared ``-created`` ordering — no ``order_by``
        # restated here. Prefetch what a row needs so a page costs a
        # constant number of queries regardless of catalogue size.
        return super().get_queryset().prefetch_related("item_names__name", "item_dates")

    def get_model_info(self):
        # django-mvp's list template writes its position line from this, as
        # "Showing 1-24 of 28 {verbose_name_plural}" directly under the page's
        # heading. Left to the model's own name, the two lines name the same
        # collection two different ways a few pixels apart.
        return {**super().get_model_info(), "verbose_name_plural": CATALOGUE_NAME_PLURAL}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # A row's role heading has to agree with the number of names under it,
        # and no template-level ``{% regroup %}`` can turn that count into the
        # right plural form in a language declaring more than two. Iterating
        # the page caches it in place, so these are the objects the template
        # goes on to render, and the grouping reads the queryset's prefetch
        # rather than querying per row.
        for page_item in context["object_list"]:
            page_item.contributor_groups = contributor_groups(page_item)

        return context


class ItemListView(CatalogueListMixin, MVPFilteredListView):
    """The catalogue list — FR-012, FR-014, FR-015, FR-018, FR-027, FR-029."""

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

    # US-1 (research R2, plan.md "The toolbar" seam): the card list has no
    # actions hook of its own, so the action row is carried by a wrapper
    # template that overrides list_view.html's page.actions block against a
    # view-supplied list, the packaged default plus import. Set here,
    # never on CatalogueListMixin — the contributor page composes that
    # mixin too and must not gain either the import action or this
    # template (FR-023, plan.md D-6).
    template_name = "literature/ui/item_list_page.html"
    directory: list[str] = ["create", "import"]
    show_import_action = True
    list_actions: list[str] = ["search", "sort", "filter", "create", "import"]

    def get_url_kwargs(self, action):
        # "import" is collection-level, like "list"/"create" — CRUDDirectoryMixin's
        # own default only special-cases those two, so on a list view (whose
        # self.kwargs is always {}) any other action falls through to
        # `dict(self.kwargs) or None`, i.e. None, and directory.import_url
        # never resolves (decisions.md D14). ItemTableView carries the same
        # override for the same reason — the two have no shared base that
        # excludes ContributorDetailView, so edit them together.
        if action == "import":
            return {}
        return super().get_url_kwargs(action)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # MVPFilteredListView.get_context_data() (mvp/integrations/django_filters/views.py)
        # already populated applied_filters/applied_filter_count above, but
        # counted the hidden "sort" field (literature/ui/filters.py
        # ItemFilterSet.sort, plan.md D-7) as an applied filter, which it is
        # not (decisions.md D21). Recomputed here through the same shared
        # exclusion ItemTableView.get_context_data() below also calls.
        if context.get("filter"):
            active = get_active_filters(self.filterset)
            context["applied_filters"] = active
            context["applied_filter_count"] = len(active)

        context["list_actions"] = self.list_actions
        return context


class ItemTableView(MVPTableViewMixin, FilterView):
    """The catalogue as a table — US-1 and US-2 (FR-001 through FR-012, FR-019 through FR-021).

    ``ItemListView`` keeps its name, its card template and its behaviour
    unchanged (plan.md D-1); this is a new, sibling view, and ``urls.py``
    points the ``item-list`` route at it. ``ContributorDetailView`` stays on
    cards through ``CatalogueListMixin`` (plan.md D-6), the configuration it
    shares with ``ItemListView`` rather than an inheritance from it, so it is
    unaffected either way (FR-023).
    """

    model = Item
    table_class = ItemTable

    # Mandatory, not inherited: MVPTableView sets no paginate_by at all, and
    # without one the catalogue becomes unpaginated and the whole footer bar
    # disappears, since it renders under `{% if page_obj %}` (research R4).
    # 24 is the card list's own page size, kept so the change of
    # presentation does not also change how much is on a page.
    paginate_by = 24

    page_title = CATALOGUE_TITLE

    # The mixin's own default was ["search", "filter", "create"] (plan.md
    # D-3) — FS-009 switched search and filter off with this attribute;
    # this feature is what reverses that. US-1 adds "import": the table
    # view has its own actions hook (research R2), so naming it here is
    # the whole change on this side of the toolbar.
    actions: list[str] = ["search", "filter", "create", "import"]
    directory: list[str] = ["create", "import"]
    show_create_action = True
    show_import_action = True
    crud_views = CRUD_VIEWS
    search_fields = SEARCH_FIELDS
    filterset_class = ItemFilterSet

    # Same flag name and semantics as ItemDetailView.show_update_action
    # (FR-020) — a project that overrides one to gate the write page
    # overrides the other the same way to gate this row control, and this
    # feature checks nothing of its own.
    show_update_action = True

    def get_url_kwargs(self, action):
        # Same reasoning as ItemListView.get_url_kwargs() (decisions.md D14)
        # — "import" is collection-level, and CRUDDirectoryMixin's default
        # only knows "list"/"create" as such. Edit the two together.
        if action == "import":
            return {}
        return super().get_url_kwargs(action)

    # No order_by: MVPTableViewMixin raises ImproperlyConfigured at
    # instantiation if it finds one — ordering lives on the table class.

    empty_state_heading = _("Nothing in the catalogue yet")
    empty_state_message = _("References imported or created will appear here.")

    # FR-028, plan.md D-8: a search or filter matching nothing reads
    # differently from a genuinely empty catalogue, and keeps its controls —
    # django-mvp's own empty state otherwise renders the same "nothing here"
    # copy either way.
    no_matches_heading = _("No references match your search")
    no_matches_message = _("Try a different search term, or clear the search and filters.")

    def get_empty_state_heading(self):
        if self.catalogue_is_narrowed():
            return self.no_matches_heading
        return super().get_empty_state_heading()

    def get_empty_state_message(self):
        if self.catalogue_is_narrowed():
            return self.no_matches_message
        return super().get_empty_state_message()

    def catalogue_is_narrowed(self):
        """Whether the current request carries a search term or a filter value.

        Read from the raw request rather than from ``self.filterset.qs``
        being empty — an empty catalogue with no query in force is a
        different circumstance from a query that matched nothing, and both
        can leave the same queryset empty. ``self.filterset`` is already
        built and bound by the time a view method reaches here
        (``BaseFilterView.get()`` sets it before calling ``get_context_data()``).
        """
        if self.request.GET.get("q", "").strip():
            return True
        return any(self.request.GET.get(name, "").strip() for name in self.filterset.filters)

    def get_queryset(self):
        # Both prefetches, not one: the credited-names cell reads
        # "contributors" (a to_attr prefetch restricted to author- and
        # editor-role rows, ordered the way ItemName.Meta already orders
        # them), and the issued cell walks the whole ItemDate row via
        # item_dates, which the card view already prefetches for the same
        # reason. Omitting either costs one query per row (plan.md D-2).
        #
        # No "issued" annotation here: ItemFilterSet.filter_queryset()
        # (literature/ui/filters.py, plan.md D-5) annotates it on every
        # request, whether or not a year was requested. Annotating it again
        # here would double-annotate the same alias.
        return (
            super()
            .get_queryset()
            .prefetch_related(
                Prefetch(
                    "item_names",
                    queryset=ItemName.objects.filter(role__in=(NameRole.AUTHOR, NameRole.EDITOR)).select_related(
                        "name"
                    ),
                    to_attr="contributors",
                ),
                "item_dates",
            )
        )

    def get_filterset_kwargs(self, filterset_class):
        # FilterMixin's default binds with `self.request.GET or None`, and
        # an empty QueryDict on a bare, param-less request is falsy — so the
        # filterset stayed unbound and filter_queryset() (and the `issued`
        # annotation it applies) never ran (decisions.md D17/D18). A
        # QueryDict is `is not None` even when empty, so passing it directly
        # keeps the filterset always bound.
        kwargs = super().get_filterset_kwargs(filterset_class)
        kwargs["data"] = self.request.GET
        return kwargs

    def get_context_data(self, **kwargs):
        """FR-016: what is in force is visible on the page (plan.md D-2).

        ``MVPFilteredListView.get_context_data()`` is what adds
        ``applied_filters``/``applied_filter_count`` for django-mvp's own
        filter-button badge (``mvp/integrations/django_filters/views.py``),
        and it never runs here — this view composes ``MVPTableViewMixin,
        FilterView`` directly rather than through that class (plan.md D-2),
        since no filtered-table equivalent of it exists. Confirmed directly
        before writing this: an unfiltered request left both keys absent
        from the context entirely. Mirrored rather than reached through a
        third mixin: multiple inheritance from both the table and the
        filtered-list bases would fight over ``get_queryset()`` and
        ``get_context_data()`` for no benefit over the lines below.
        """
        context = super().get_context_data(**kwargs)
        if context.get("filter") and hasattr(self.filterset.form, "cleaned_data"):
            # get_active_filters() (literature/ui/filters.py) is the one
            # place the exclusion of "sort" — the table's own ordering,
            # carried as a hidden field on this form so it survives a change
            # of filter — from what counts as an applied filter is declared
            # (decisions.md D20's own correction, D21). ItemListView.
            # get_context_data() calls the same function.
            active = get_active_filters(self.filterset)
            context["applied_filters"] = active
            context["applied_filter_count"] = len(active)
        return context

    def get_model_info(self):
        # Same reasoning as ItemListView.get_model_info(): the table
        # template's own position line otherwise reads "of 28 items"
        # directly under a heading that says Publications.
        return {**super().get_model_info(), "verbose_name_plural": CATALOGUE_NAME_PLURAL}

    def get_table_kwargs(self):
        # show_action("update") is CRUDDirectoryMixin's own method, read
        # here directly rather than through get_directory()/"directory" —
        # that dict resolves a URL for *this* view's own single object and
        # is empty for a list view's kwargs (FR-020, literature/ui/tables.py
        # ItemTable.__init__).
        return {**super().get_table_kwargs(), "show_update_action": self.show_action("update")}


class ItemCreateView(MVPCreateView):
    """Enter a reference by hand — US-1 (FR-001 through FR-011)."""

    model = Item
    form_class = ItemForm
    template_name = "literature/ui/item_form.html"

    # Item has no get_absolute_url(), so success_url is mandatory (D-6). The
    # "detail" shorthand only resolves once show_detail_action is set —
    # without it, get_success_url() falls through to the literal relative
    # path "detail" and 404s. Both flags are also what get_breadcrumbs()
    # needs to reverse "list" and "detail" without raising NoReverseMatch.
    success_url = "detail"
    show_list_action = True
    show_detail_action = True
    crud_views = CRUD_VIEWS

    page_title = _("Add %(verbose_name)s")
    success_message = _("%(verbose_name)s added to the catalogue.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(field_group_context(context["form"]))
        return context


#: The two session keys carrying a staged file's identity across the
#: preview → confirm round trip (US-4, FR-042). Never in the page, never in
#: ``ConfirmImportForm`` — a request can only confirm what its own session
#: staged, because this is the only place the token is ever written down
#: (decisions.md D16).
IMPORT_TOKEN_SESSION_KEY = "literature_import_token"  # noqa: S105 — a session key name, not a secret
IMPORT_FORMAT_SESSION_KEY = "literature_import_format"


class ItemImportView(MVPFormView):
    """Choose a format and a file, and preview what it would do by default
    (US-1, US-4, FR-005, FR-006, FR-010, FR-019, FR-023, FR-038 through
    FR-040).

    ``model = Item`` even though the form below is not a ``ModelForm``:
    ``MVPFormView``'s context machinery raises ``ImproperlyConfigured`` on
    first render with no model at all (research.md R3), and the page's
    breadcrumb genuinely belongs under the catalogue.
    """

    model = Item
    form_class = ImportForm
    template_name = "literature/ui/import_form.html"
    list_view_title = CATALOGUE_TITLE
    page_title = _("Import references")

    def dispatch(self, request, *args, **kwargs):
        # Every entry to this view, GET or POST, sweeps abandoned stagings
        # first (T507) — removal after a successful confirm is not the only
        # cleanup path (FR-043).
        StagedUpload().sweep()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # get_format() returns the class; import_file() is an instance
        # method (research.md "The view" seam) — the format is resolved by
        # name and instantiated fresh for this one run, never cached.
        format_name = form.cleaned_data["format"]
        format_class = get_format(format_name)
        context = self.get_context_data(form=form)

        if form.cleaned_data["skip_preview"]:
            result = format_class().import_file(form.cleaned_data["file"])
            return self._render_report(context, result, preview=False)

        staging = StagedUpload()
        token = staging.save(form.cleaned_data["file"])
        self.request.session[IMPORT_TOKEN_SESSION_KEY] = token
        self.request.session[IMPORT_FORMAT_SESSION_KEY] = format_name

        with staging.open(token) as handle:
            result = format_class().import_file(handle, dry_run=True)

        return self._render_report(context, result, preview=True)

    def _render_report(self, context, result, *, preview):
        # Rendered directly, never through get_success_url()/redirect: the
        # reader always lands on the report, and a GET reload re-submitting
        # the form is the browser's own resubmission prompt, not a control
        # this page offers (FR-023, decisions.md D1, D11).
        report = ImportReport(result)
        context["report"] = report
        context["table"] = ImportReportTable(report.rows)
        context["preview"] = preview
        return render(self.request, "literature/ui/import_report.html", context)


class ItemImportConfirmView(MVPFormView):
    """Carry out the import a preview described (US-4, FR-041 through FR-044).

    ``ConfirmImportForm`` declares no field: the staged file's token and the
    format it was staged as both come from the reader's own session, never
    from this page (decisions.md D16). A GET here has nothing to show
    without a prior preview, so it sends the reader back to the import page
    rather than rendering a template of its own.
    """

    model = Item
    form_class = ConfirmImportForm
    template_name = "literature/ui/import_form.html"
    list_view_title = CATALOGUE_TITLE
    page_title = _("Confirm import")

    def get(self, request, *args, **kwargs):
        return redirect("literature:item-import")

    def form_valid(self, form):
        token = self.request.session.pop(IMPORT_TOKEN_SESSION_KEY, None)
        format_name = self.request.session.pop(IMPORT_FORMAT_SESSION_KEY, None)

        staging = StagedUpload()
        handle = staging.open(token) if token else None
        context = self.get_context_data(form=form)

        if handle is None:
            # Nothing this session staged, or it has already been confirmed
            # or swept — either way there is nothing to import (FR-044).
            context["nothing_to_confirm"] = True
            return render(self.request, "literature/ui/import_report.html", context)

        with handle:
            result = get_format(format_name)().import_file(handle)
        staging.discard(token)

        report = ImportReport(result)
        context["report"] = report
        context["table"] = ImportReportTable(report.rows)
        context["preview"] = False
        return render(self.request, "literature/ui/import_report.html", context)


class ItemUpdateView(MVPUpdateView):
    """Correct a reference that is wrong — US-2 (FR-009 through FR-014)."""

    model = Item
    form_class = ItemForm
    template_name = "literature/ui/item_form.html"

    # Same shorthand and same reasoning as ItemCreateView (D-6): Item has no
    # get_absolute_url(), so success_url is mandatory, and the "detail"
    # shorthand only resolves once show_detail_action is set. Both flags are
    # also what get_breadcrumbs() needs to reverse "list" and "detail".
    success_url = "detail"
    show_list_action = True
    show_detail_action = True
    crud_views = CRUD_VIEWS

    page_title = _("Edit %(verbose_name)s")
    success_message = _("%(verbose_name)s updated.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # groups_holding_values(self.object) is the forced-visible set
        # FR-010/FR-014 ask for — a group the stored type would not
        # otherwise show still renders when a value already lives in it.
        context.update(field_group_context(context["form"], FieldGroups.groups_holding_values(self.object)))
        return context


class ItemDetailView(MVPDetailView):
    """The reference page — FR-019, FR-025, FR-027."""

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

    # "delete" is named per plan.md D-6's table (matching MVPDetailView's own
    # default directory). show_delete_action stayed unset through US-2
    # (decisions.md D13) because ItemDeleteView and its route did not exist
    # yet — turning the flag on ahead of the route would have turned every
    # reference-page request into a NoReverseMatch. Both now exist (US-3).
    directory: list[str] = ["update", "delete"]
    show_update_action = True
    show_delete_action = True

    # CRUD_VIEWS replaces the former two-key override (D-6, DR-006): every
    # view now shares the same namespaced mapping, so "every name in every
    # view's crud_views reverses" no longer depends on which keys a partial
    # per-view override happened to name.
    crud_views = CRUD_VIEWS

    def get_queryset(self):
        return super().get_queryset().prefetch_related("item_names__name", "item_dates", "item_identifiers")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["scalar_fields"] = list(scalar_fields(self.object))
        context["contributor_groups"] = contributor_groups(self.object)

        # Whether an identifier may be rendered as a link is decided here,
        # against a scheme allowlist, and never in the template: a template
        # can only ask whether the value *looks* like a URL, and
        # ``javascript://x`` passes that test (RS-001). Annotating the
        # instances reuses the queryset's prefetch, so this costs no query.
        identifiers = list(self.object.item_identifiers.all())
        for identifier in identifiers:
            identifier.href = web_url(identifier.value)
        context["identifiers"] = identifiers
        return context


class ItemDeleteView(MVPDeleteView):
    """Remove a reference that does not belong — US-3 (FR-017 through FR-020)."""

    model = Item

    # FR-019 — lists what cascades (the ItemName/ItemDate/ItemIdentifier rows
    # that go with the reference) before the reader commits (plan.md D-7).
    # require_confirmation stays off: typing a value to confirm is friction
    # this feature has no case for. Name records are never listed here and
    # are never touched by the cascade — nothing points from Item to Name
    # directly, only ItemName rows do (FR-020, D-7).
    show_related_objects = True

    # Item has no get_absolute_url(), so success_url is mandatory (D-6); the
    # "list" shorthand only resolves once show_list_action is set.
    # show_detail_action is what get_back_url() below needs to resolve the
    # "detail" shorthand.
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
        catalogue instead of the reference it was considering removing
        (FR-018, plan.md D-7). Overridden to fall through to the ``detail``
        shorthand instead — the object still exists at GET time, so its own
        URL is always resolvable.
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
    """The contributor page — FR-032 through FR-038.

    A contributor's page is the catalogue filtered to what they are credited
    on, so it *is* a list view: it composes ``CatalogueListMixin`` rather
    than reproducing the card list's configuration. Pagination, the page
    size, the empty state, the grid configuration and the not-found on an
    out-of-range page all arrive with ``MVPListView``. Plain, not
    ``MVPFilteredListView``: this page carries no search box and no filter
    (FR-025, plan.md D-6) — ``ItemListView`` is the only concrete view that
    composes the mixin with a filtered base. The contributor is the page's
    subject, not the object it lists, which is the only thing here the base
    class does not already know.
    """

    list_item_template = "literature/ui/contributor_item.html"

    empty_state_heading = _("Not credited on anything yet")
    empty_state_message = _("This contributor has no credited references in the catalogue.")

    @cached_property
    def contributor(self):
        # FR-037's not-found. Resolved once per request, and before the
        # queryset is built, so a page for a contributor that does not exist
        # 404s rather than rendering an empty catalogue.
        return get_object_or_404(Name, pk=self.kwargs["pk"])

    def get_queryset(self):
        # .distinct() is load-bearing: a contributor holding two roles on one
        # item has two ItemName rows, and without it the item would appear
        # twice (FR-035). The catalogue's own ordering and prefetching come
        # from CatalogueListMixin, which is what FR-036 asks for.
        return super().get_queryset().filter(item_names__name=self.contributor).distinct()

    def get_page_title(self):
        # The name as the store holds it (FR-033) — Name.__str__ renders an
        # unparsed or institutional name without splitting it.
        return str(self.contributor)

    def get_breadcrumbs(self):
        return [
            {"text": CATALOGUE_TITLE, "href": reverse("literature:item-list")},
            {"text": self.get_page_title()},
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # list() forces the page's queryset now, caching it in place — the
        # objects annotated below are the ones the template iterates, so the
        # annotation costs no extra query.
        items_on_page = list(context["object_list"])

        # The role(s) *this* contributor held on each item, from a single
        # further query — not one per row.
        roles_by_item = defaultdict(list)
        for item_name in ItemName.objects.filter(name=self.contributor, item__in=items_on_page):
            roles_by_item[item_name.item_id].append(item_name.get_role_display())
        for page_item in items_on_page:
            page_item.credited_roles = roles_by_item[page_item.id]

        return context
