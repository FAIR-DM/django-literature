"""Demo-only pages that show the package's pieces inside a host page."""

from django.views.generic import TemplateView

from literature.models import Item

#: The references the embedding page shows, each chosen for a state the
#: reference component has to answer for.
RELATED_KEYS = [
    "Shannon1948",  # one author, journal with volume, issue and pages
    "Vaswani2017",  # eight authors, conference paper
    "Bowker2013",  # long title, a chapter in an edited book
    "Wessel2019",  # editors only, four of them
    "Ship2010",  # a dataset with a publisher and no container
    "IHFC2024",  # an organisation as author, no DOI
    "Beowulf",  # no contributors, no date, no DOI
]


class EmbeddingView(TemplateView):
    """A stand-in host page, such as a dataset's, that shows references from the catalogue."""

    template_name = "demo/embedding.html"

    def get_context_data(self, **kwargs):
        """Load the references once, with what the component reads prefetched."""
        context = super().get_context_data(**kwargs)
        items = {
            item.citation_key: item
            for item in Item.objects.filter(citation_key__in=RELATED_KEYS).prefetch_related(
                "item_names__name", "item_dates", "item_identifiers"
            )
        }
        context["related"] = [items[key] for key in RELATED_KEYS if key in items]
        context["data_publication"] = items.get("Ship2010")
        context["page_title"] = "Example dataset page"
        return context
