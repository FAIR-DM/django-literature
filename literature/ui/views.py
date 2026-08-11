"""Views for the opt-in front end.

Filled in one class per story: ``ItemListView`` (US-1), ``ItemDetailView``
(US-2), ``ContributorDetailView`` (US-4).
"""

from collections import defaultdict

from django.core.paginator import InvalidPage, Paginator
from django.http import Http404
from django.utils.translation import gettext_lazy as _
from mvp.views import MVPDetailView, MVPListView

from literature.models import Item, ItemName, Name
from literature.ui.fields import scalar_fields
from literature.ui.links import web_url


class ItemListView(MVPListView):
    """The catalogue list — FR-012, FR-014, FR-015, FR-018, FR-027, FR-029."""

    model = Item
    template_name = "literature/ui/item_list.html"
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


class ContributorDetailView(MVPDetailView):
    """The contributor page — FR-032 through FR-038."""

    model = Name
    template_name = "literature/ui/contributor_detail.html"
    list_item_template = "literature/ui/contributor_item.html"

    # Same page size as the catalogue (FR-036) — read off ItemListView's own
    # default rather than restating 24 here, so the two lists cannot drift
    # out of step.
    paginate_by = ItemListView.paginate_by

    # Reverses the breadcrumb's list link, same as ItemDetailView.
    show_list_action = True

    # A read-only page — MVPDetailView's default (['update', 'delete']) does
    # not apply.
    directory: list[str] = []

    # A NEW dict, not a mutation of the shared MVP_CONFIG one (see
    # ItemDetailView for the same note). Literal target names, not
    # '{model_name}-list'/'{model_name}-detail': this view's model is Name,
    # and 'name-list'/'name-detail' are not routes this app has.
    crud_views = {
        **MVPDetailView.crud_views,
        "list": "literature:item-list",
        "detail": "literature:contributor-detail",
    }

    empty_state_heading = _("Not credited on anything yet")
    empty_state_message = _("This contributor has no credited references in the catalogue.")

    def get_list_title(self):
        # This page's "list" is the catalogue (an Item list), not a Name list,
        # so the breadcrumb reads as it does on the reference page rather than
        # the model-derived default ("Names"). Resolved per request, not in the
        # class body: verbose_name_plural is a lazy translation, and calling
        # .title() on it at import time would freeze one language into the
        # class for the life of the process.
        return Item._meta.verbose_name_plural.title()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # MVPDetailView does not paginate — build a Paginator by hand over
        # the items this contributor is credited on, in the catalogue's
        # order. .distinct() is load-bearing: a contributor holding two
        # roles on one item has two ItemName rows, and without it the item
        # would appear twice (FR-035). The prefetch matches the catalogue
        # list's, because FR-034 gives a credit row the same content a
        # catalogue row carries.
        items = (
            Item.objects.filter(item_names__name=self.object)
            .distinct()
            .prefetch_related("item_names__name", "item_dates")
        )
        paginator = Paginator(items, self.paginate_by)
        try:
            page_obj = paginator.page(self.request.GET.get("page", 1))
        except InvalidPage as exc:
            # Paginator.get_page() would silently clamp an out-of-range page
            # to the last one — FR-036 requires a 404 instead.
            raise Http404(str(exc)) from exc

        # list() forces evaluation now, caching page_obj.object_list's
        # queryset in place — the objects annotated below are the same ones
        # the template iterates later, so no extra query is spent doing it.
        items_on_page = list(page_obj.object_list)

        # The role(s) *this* contributor held on each item, from a single
        # further query — not one per row.
        roles_by_item = defaultdict(list)
        for item_name in ItemName.objects.filter(name=self.object, item__in=items_on_page):
            roles_by_item[item_name.item_id].append(item_name.get_role_display())
        for page_item in items_on_page:
            page_item.credited_roles = roles_by_item[page_item.id]

        context["page_obj"] = page_obj
        # MVPListViewMixin.get_context_data (mvp/views/list.py) is what
        # normally sets these three keys — a DetailView never mixes it in,
        # so they are set explicitly here instead (see the story brief).
        context["grid_config"] = {}
        context["list_item_template"] = self.list_item_template
        context["empty_state"] = {
            "heading": self.empty_state_heading,
            "message": self.empty_state_message,
        }
        return context
