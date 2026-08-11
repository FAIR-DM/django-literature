"""Views for the opt-in front end.

Filled in one class per story: ``ItemListView`` (US-1), ``ItemDetailView``
(US-2), ``ContributorDetailView`` (US-4).
"""

from django.utils.translation import gettext_lazy as _
from mvp.views import MVPListView

from literature.models import Item


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
