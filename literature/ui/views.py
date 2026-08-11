"""Views for the opt-in front end.

Filled in one class per story: ``ItemListView`` (US-1), ``ItemDetailView``
(US-2), ``ContributorDetailView`` (US-4).
"""

from django.utils.translation import gettext_lazy as _
from mvp.views import MVPDetailView, MVPListView

from literature.models import Item
from literature.ui.fields import scalar_fields


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
        return context
