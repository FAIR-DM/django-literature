"""How the write form is arranged on the page: tabs, sections and the copy a person reads.

Kept apart from ``forms.py`` so that the form stays the list of fields it
saves, and this module the one place that says where each of them is drawn.
Every field is placed exactly once, so a field the current item type does not
use is still in the page, still posts the value it held, and a save that
changed nothing changes nothing (FS-008).
"""

from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Column, Div, Layout, Row
from django.utils.translation import gettext_lazy as _
from mvp_forms.layout import Fieldset, Tab, TabHolder

from literature.choices import DateType, ItemType, NameRole
from literature.ui.contributors import ContributorGroups
from literature.ui.fieldgroups import GROUP_LABELS, GROUPS, ROLE_ORDER

#: The 45 item types in eight groups a person scans by, rather than one
#: alphabetical run where "Journal Article" sits between "Interview" and
#: "Legal Case".
TYPE_GROUPS_FOR_CHOOSING = (
    (
        _("Articles"),
        (
            ItemType.ARTICLE_JOURNAL,
            ItemType.ARTICLE_MAGAZINE,
            ItemType.ARTICLE_NEWSPAPER,
            ItemType.ARTICLE,
            ItemType.REVIEW,
            ItemType.REVIEW_BOOK,
        ),
    ),
    (
        _("Books and reference works"),
        (
            ItemType.BOOK,
            ItemType.CHAPTER,
            ItemType.ENTRY_ENCYCLOPEDIA,
            ItemType.ENTRY_DICTIONARY,
            ItemType.ENTRY,
            ItemType.CLASSIC,
            ItemType.COLLECTION,
            ItemType.PAMPHLET,
            ItemType.PERIODICAL,
        ),
    ),
    (
        _("Conferences and events"),
        (
            ItemType.PAPER_CONFERENCE,
            ItemType.SPEECH,
            ItemType.EVENT,
            ItemType.PERFORMANCE,
        ),
    ),
    (
        _("Reports and unpublished work"),
        (
            ItemType.REPORT,
            ItemType.THESIS,
            ItemType.STANDARD,
            ItemType.MANUSCRIPT,
            ItemType.PERSONAL_COMMUNICATION,
            ItemType.DOCUMENT,
        ),
    ),
    (_("Data and software"), (ItemType.DATASET, ItemType.SOFTWARE)),
    (_("Web"), (ItemType.WEBPAGE, ItemType.POST_WEBLOG, ItemType.POST)),
    (
        _("Legal"),
        (
            ItemType.LEGAL_CASE,
            ItemType.LEGISLATION,
            ItemType.BILL,
            ItemType.REGULATION,
            ItemType.HEARING,
            ItemType.TREATY,
            ItemType.PATENT,
        ),
    ),
    (
        _("Media, images and maps"),
        (
            ItemType.BROADCAST,
            ItemType.MOTION_PICTURE,
            ItemType.INTERVIEW,
            ItemType.SONG,
            ItemType.MUSICAL_SCORE,
            ItemType.FIGURE,
            ItemType.GRAPHIC,
            ItemType.MAP,
        ),
    ),
)

TYPE_CHOICE_GROUPS = [
    (heading, [(item_type.value, item_type.label) for item_type in types])
    for heading, types in TYPE_GROUPS_FOR_CHOOSING
]

#: Labels where the model's ``verbose_name`` is the CSL variable's name rather
#: than what a person would call it.
FIELD_LABELS = {
    "container_title": _("Title"),
    "container_title_short": _("Short title"),
    "collection_title": _("Series"),
    "collection_number": _("Number in series"),
    "page": _("Pages"),
    "page_first": _("First page"),
    "publisher_place": _("Place of publication"),
    "original_publisher_place": _("Original place of publication"),
    "event_title": _("Event"),
    "event_place": _("Place"),
    "reviewed_title": _("Title of the reviewed work"),
    "reviewed_genre": _("Reviewed genre"),
    "references": _("Procedural history"),
    "archive_collection": _("Collection"),
    "archive_location": _("Location in the archive"),
    "archive_place": _("Place of the archive"),
    "status": _("Publication status"),
    "keyword": _("Keywords"),
    "annote": _("Annotation"),
    "title_short": _("Short title"),
    "volume_title_short": _("Short volume title"),
}

#: Help only where a label alone leaves the person guessing. Every other field
#: draws none, rather than the model's CSL JSON mapping note.
FIELD_HELP = {
    "citation_key": _(
        "A short handle for citing it, such as shannon1948. It need not be unique."
    ),
    "container_title": _("The journal, book, website or programme it appeared in."),
    "journal_abbreviation": _(
        "As citation styles print it, such as Bell Syst. Tech. J."
    ),
    "page": _("A single page or a range, such as 379–423."),  # noqa: RUF001
    "number": _("A report, patent, bill or standard number."),
    "edition": _("Such as 2nd or revised."),
    "version": _("Of software or a dataset, such as 2.1.0."),
    "medium": _("Such as print, CD or online."),
    "genre": _("Such as PhD thesis or technical report."),
    "event_title": _("The conference, exhibition or other event."),
    "reviewed_genre": _("Such as book or film."),
    "authority": _("The court, agency or office that issued it."),
    "jurisdiction": _("Such as a country or state."),
    "archive_location": _("Such as a box and folder."),
    "dimensions": _("Such as 30 × 40 cm, or a running time."),  # noqa: RUF001
    "scale": _("Such as 1:50,000."),
    "status": _("Only for work not yet published, such as forthcoming or in press."),
    "language": _("A language tag, such as en or de."),
    "keyword": _("Separate keywords with commas."),
    "note": _("Some citation styles print this after the reference."),
    "annote": _("For an annotated bibliography."),
    "source": _("The library catalogue or database it was found in."),
    "title_short": _(
        "For citation styles that cite a work in short after its first mention."
    ),
    "original_title": _("Its title in the original language, for a translation."),
}

#: The order the item-type sections take on the page, which is the order a
#: citation reads them in: where it appeared, its volume and pages, who
#: published it, and the rest after.
SECTION_ORDER = (
    "container",
    "numbering",
    "publication",
    "original",
    "event",
    "review",
    "legal",
    "archive",
    "physical",
)

#: The numbering fields drawn without opening anything. The other nine are
#: rarer and sit under "More numbering".
LEADING_NUMBERING = ("volume", "issue", "page", "number")


#: The six CSL date slots as they read on the form, in the order a reference's
#: life runs.
DATE_SLOTS = (
    (DateType.SUBMITTED, _("Submitted")),
    (DateType.ISSUED, _("Published")),
    (DateType.AVAILABLE_DATE, _("Available online")),
    (DateType.EVENT_DATE, _("Event date")),
    (DateType.ORIGINAL_DATE, _("Originally published")),
    (DateType.ACCESSED, _("Accessed")),
)


def date_field_name(slot, end=False):
    """Return the form field name for a date slot's start, or its end."""
    name = "date_" + slot.replace("-", "_")
    return name + "_end" if end else name


def shown_when(group):
    """Return the Alpine condition under which an item-type section is shown."""
    return (
        "form.showAll"
        f" || (form.forcedGroups || []).includes('{group}')"
        f" || (form.typeGroups[form.itemType] || []).includes('{group}')"
    )


def date_shown_when(slot):
    """Return the Alpine condition under which a date slot is shown. Published always is."""
    if slot == DateType.ISSUED:
        return "true"
    return (
        "form.showAll"
        f" || (form.forcedDates || []).includes('{slot}')"
        f" || (form.typeDates[form.itemType] || []).includes('{slot}')"
    )


def role_shown_when(role):
    """Return the Alpine condition under which a contributor role's set is shown. Authors always are."""
    if role == NameRole.AUTHOR:
        return "true"
    return (
        "form.showAllRoles"
        f" || (form.forcedRoles || []).includes('{role}')"
        f" || (form.typeRoles[form.itemType] || []).includes('{role}')"
    )


def rows_of(names, per_row):
    """Lay ``names`` out ``per_row`` to a row, each in an equal column."""
    names = list(names)
    return [
        Row(*(Column(name) for name in names[start : start + per_row]))
        for start in range(0, len(names), per_row)
    ]


def include(template):
    """Draw another template in place, with the page's own context."""
    return HTML(f'{{% include "{template}" %}}')


class ItemFormLayout:
    """The write form's arrangement, for one form instance.

    Four tabs: the reference itself, its contributors, its identifiers, and
    notes with the fields most references never need. The fields citation
    software sets (``GROUPS["processor"]``) are not on the form at all.
    """

    def __init__(self, form):
        self.form = form

    def holds_value(self, name):
        """Whether the field already holds something, on this form's own data."""
        value = self.form[name].value()
        return value not in (None, "", False)

    def section(self, group):
        """One item-type section: a fieldset shown when the chosen type uses it."""
        fields = GROUPS[group]
        if group == "numbering":
            rest = [name for name in fields if name not in LEADING_NUMBERING]
            body = [
                Row(*(Column(name) for name in LEADING_NUMBERING)),
                Fieldset(
                    _("More numbering"),
                    *rows_of(rest, 3),
                    css_id="item-more-numbering",
                    collapsible=True,
                    open=any(self.holds_value(name) for name in rest),
                ),
            ]
        elif group == "container":
            body = [
                "container_title",
                Row(Column("container_title_short"), Column("journal_abbreviation")),
                Row(Column("collection_title"), Column("collection_number")),
            ]
        elif group == "legal":
            body = [*rows_of(fields[:3], 3), "references"]
        else:
            body = rows_of(fields, 2 if len(fields) % 2 == 0 else 3)
        return Fieldset(
            GROUP_LABELS[group],
            *body,
            css_id=f"item-section-{group}",
            collapsible=True,
            open=True,
            x_show=shown_when(group),
        )

    def dates(self):
        """One date field per CSL date slot, each shown when the type uses it.

        An end date is offered for an event, whose dates are often a range,
        and for any slot that already holds one.
        """
        slots = []
        for slot, _label in DATE_SLOTS:
            end = date_field_name(slot, end=True)
            with_end = slot == "event-date" or self.holds_value(end)
            slots.append(
                Div(
                    Row(
                        Column(date_field_name(slot)),
                        Column(end, css_class="" if with_end else "hidden"),
                    ),
                    css_id=f"item-date-{slot}",
                    x_show=date_shown_when(slot),
                )
            )
        return Fieldset(
            _("Dates"),
            *slots,
            description=_("A year alone is enough."),
            css_id="item-section-dates",
            collapsible=True,
            open=True,
        )

    def reference_tab(self):
        """What the reference is, in the order a citation reads it, then what it is about."""
        return Tab(
            _("Reference"),
            Row(Column("type"), Column("citation_key")),
            "title",
            Row(Column("status"), Column("language")),
            include("literature/ui/item_form_type_hint.html"),
            *(self.section(group) for group in SECTION_ORDER),
            include("literature/ui/item_form_show_all.html"),
            self.dates(),
            Fieldset(
                _("Abstract and keywords"),
                "abstract",
                "keyword",
                collapsible=True,
                open=True,
            ),
            css_id="item-tab-reference",
        )

    def contributors_tab(self):
        """Who made it, in the order they are credited."""
        sets = [
            Fieldset(
                ContributorGroups.role_label(role, 2),
                HTML(
                    "{% include 'literature/ui/item_form_contributors.html'"
                    f" with formset=contributor_sets.{index} %}}"
                ),
                css_id=f"item-role-{role}",
                collapsible=True,
                open=True,
                x_show=role_shown_when(role),
            )
            for index, role in enumerate(ROLE_ORDER)
        ]
        return Tab(
            _("Contributors"),
            include("literature/ui/item_form_contributor_intro.html"),
            *sets,
            include("literature/ui/item_form_show_all_roles.html"),
            css_id="item-tab-contributors",
        )

    def identifiers_tab(self):
        """DOI, ISBN, URL and any other identifier."""
        return Tab(
            _("Identifiers"),
            include("literature/ui/item_form_identifiers.html"),
            css_id="item-tab-identifiers",
        )

    def more_tab(self):
        """Notes, and the fields most references never need, closed until they are."""

        def closed(name, fields):
            return Fieldset(
                name,
                *fields,
                collapsible=True,
                open=any(self.holds_value(field) for field in fields),
            )

        return Tab(
            _("More"),
            Fieldset(_("Notes"), "note", "annote", collapsible=True, open=True),
            closed(_("Alternate titles"), GROUPS["titles"]),
            closed(_("Library and database"), ("source", "call_number")),
            css_id="item-tab-more",
        )

    def helper(self):
        """Return the form helper that draws the whole arrangement."""
        helper = FormHelper(self.form)
        helper.form_tag = False
        helper.disable_csrf = True
        helper.layout = Layout(
            TabHolder(
                self.reference_tab(),
                self.contributors_tab(),
                self.identifiers_tab(),
                self.more_tab(),
            )
        )
        return helper
