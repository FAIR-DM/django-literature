"""Views for the opt-in front end.

Filled in one class per story: ``ItemListView`` (US-1), ``ItemDetailView``
(US-2), ``ContributorDetailView`` (US-4), ``ItemCreateView`` (US-1 again),
``ItemUpdateView`` (US-2 again), ``ItemDeleteView`` (US-3).
"""

import json
from collections import defaultdict
from functools import cached_property

from django.db.models import OuterRef, Prefetch, Subquery
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from mvp.integrations.django_tables.views import MVPTableView
from mvp.views import MVPCreateView, MVPDeleteView, MVPDetailView, MVPListView, MVPUpdateView

from literature.choices import DateType, ItemType, NameRole
from literature.models import Item, ItemDate, ItemName, Name
from literature.ui.contributors import contributor_groups
from literature.ui.fieldgroups import FieldGroups
from literature.ui.fields import scalar_fields
from literature.ui.forms import ItemForm
from literature.ui.links import web_url
from literature.ui.tables import ItemTable

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


class ItemListView(MVPListView):
    """The catalogue list — FR-012, FR-014, FR-015, FR-018, FR-027, FR-029."""

    model = Item
    page_title = CATALOGUE_TITLE
    # No ``template_name``: the page renders through django-mvp's own
    # ``list_view.html``, which reaches the shell through the default
    # ``base.html`` django-mvp has shipped since 0.18 — this app carried a
    # pass-through of its own until then. Only the card is ours.
    list_item_template = "literature/ui/item_list_item.html"

    # Out of scope here (#49) — set explicitly so a later template change
    # cannot resurrect a control this feature excluded (plan.md D-2).
    search_fields = None
    order_by = None

    # "create" alone in directory shows nothing without the matching
    # show_create_action flag (plan.md D-6) — CRUDDirectoryMixin defaults
    # every show_<action>_action to False and drops the entry silently.
    # create_form_class stays unset on purpose: a thirteen-group form does
    # not belong in the list component's modal (plan.md D-8), so the
    # component instead renders a plain link to the create page.
    directory: list[str] = ["create"]
    show_create_action = True
    crud_views = CRUD_VIEWS

    empty_state_heading = _("Nothing in the catalogue yet")
    empty_state_message = _("References imported or created will appear here.")

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


class ItemTableView(MVPTableView):
    """The catalogue as a table — US-1 and US-2 (FR-001 through FR-012, FR-019 through FR-021).

    ``ItemListView`` keeps its name, its card template and its behaviour
    unchanged (plan.md D-1); this is a new, sibling view, and ``urls.py``
    points the ``item-list`` route at it. ``ContributorDetailView`` goes on
    subclassing ``ItemListView``, so it stays on cards with no change of its
    own (FR-023).
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

    # The mixin's own default is ["search", "filter", "create"]. Search is
    # #49's and filter renders nothing on a non-FilterView anyway, but both
    # are named out explicitly, for the same reason ItemListView already
    # names search_fields out explicitly: so a later change to an upstream
    # default cannot put an unspecified control on the package's default
    # page (FR-025).
    actions = ["create"]
    directory: list[str] = ["create"]
    show_create_action = True
    crud_views = CRUD_VIEWS
    search_fields = None

    # Same flag name and semantics as ItemDetailView.show_update_action
    # (FR-020) — a project that overrides one to gate the write page
    # overrides the other the same way to gate this row control, and this
    # feature checks nothing of its own.
    show_update_action = True

    # No order_by: MVPTableViewMixin raises ImproperlyConfigured at
    # instantiation if it finds one — ordering lives on the table class.

    empty_state_heading = _("Nothing in the catalogue yet")
    empty_state_message = _("References imported or created will appear here.")

    def get_queryset(self):
        # Both prefetches, not one: the credited-names cell reads
        # "contributors" (a to_attr prefetch restricted to author- and
        # editor-role rows, ordered the way ItemName.Meta already orders
        # them), and the issued cell walks the whole ItemDate row via
        # item_dates, which the card view already prefetches for the same
        # reason. Omitting either costs one query per row (plan.md D-2).
        #
        # "issued" is a Subquery annotation, not a join filter (plan.md D-8,
        # research R7): a join risks row multiplication when an item carries
        # several ItemDate rows and interferes with the paginator's count
        # query. ItemTable.order_issued() (US-3) sorts on this column.
        issued_begin = ItemDate.objects.filter(item=OuterRef("pk"), date_type=DateType.ISSUED).values("begin")[:1]
        return (
            super()
            .get_queryset()
            .annotate(issued=Subquery(issued_begin))
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


class ContributorDetailView(ItemListView):
    """The contributor page — FR-032 through FR-038.

    A contributor's page is the catalogue filtered to what they are credited
    on, so it *is* a list view: it subclasses the catalogue rather than
    reproducing it. Pagination, the page size, the empty state, the grid
    configuration and the not-found on an out-of-range page all arrive with
    ``MVPListView``. The contributor is the page's subject, not the object it
    lists, which is the only thing here the base class does not already know.
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
        # from ItemListView, which is what FR-036 asks for.
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
