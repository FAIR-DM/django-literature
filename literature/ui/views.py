"""Views for the opt-in front end.

Filled in one class per story: ``ItemListView`` (US-1), ``ItemDetailView``
(US-2), ``ContributorDetailView`` (US-4).
"""

from collections import defaultdict
from functools import cached_property

from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from mvp.views import MVPDetailView, MVPListView

from literature.models import Item, ItemName, Name
from literature.ui.fields import scalar_fields
from literature.ui.links import web_url


class ItemListView(MVPListView):
    """The catalogue list — FR-012, FR-014, FR-015, FR-018, FR-027, FR-029."""

    model = Item
    # No ``template_name``: the page renders through django-mvp's own
    # ``list_view.html``, which the package reaches via the pass-through
    # ``base.html`` this app ships until django-mvp carries a default of its
    # own. Only the card is ours.
    list_item_template = "literature/ui/item_list_item.html"

    # Out of scope here (#49) — set explicitly so a later template change
    # cannot resurrect a control this feature excluded (plan.md D-2).
    search_fields = None
    order_by = None
    directory: list[str] = []

    empty_state_heading = _("Nothing in the catalogue yet")
    empty_state_message = _("References imported or created will appear here.")

    def get_queryset(self):
        # Keep the model's declared ``-created`` ordering — no ``order_by``
        # restated here. Prefetch what a row needs so a page costs a
        # constant number of queries regardless of catalogue size.
        return super().get_queryset().prefetch_related("item_names__name", "item_dates")


class ItemDetailView(MVPDetailView):
    """The reference page — FR-019, FR-025, FR-027."""

    model = Item
    template_name = "literature/ui/item_detail.html"

    # Reverses the breadcrumb's list link. The default False leaves it
    # href-less: PageObjectMixin.get_breadcrumbs() calls resolve_crud_url("list")
    # regardless, and show_list_action gates whether that call is even attempted.
    show_list_action = True
    directory: list[str] = []

    # MVPDetailView.crud_views is MVP_CONFIG["view_names"] itself — a dict
    # shared process-wide. Building a new one here (rather than assigning
    # into it) avoids reconfiguring django-mvp for every other view.
    # The plain entries carry no namespace ('{model_name}-list'), so
    # resolve_crud_url's plain reverse('item-list') raises NoReverseMatch
    # under this app's namespaced urls.py (app_name = "literature").
    crud_views = {
        **MVPDetailView.crud_views,
        "list": "literature:{model_name}-list",
        "detail": "literature:{model_name}-detail",
    }

    def get_queryset(self):
        return super().get_queryset().prefetch_related("item_names__name", "item_dates", "item_identifiers")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["scalar_fields"] = list(scalar_fields(self.object))

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
            {"text": Item._meta.verbose_name_plural.title(), "href": reverse("literature:item-list")},
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
