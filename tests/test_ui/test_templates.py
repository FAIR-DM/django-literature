"""Tests for the templates ``literature.ui`` ships."""

import re
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory
from django.urls import reverse
from django_cotton import render_component
from partial_date import PartialDate

from literature.choices import DateType, IdentifierType, NameRole
from literature.models import Item
from literature.ui.tables import OutcomeColumn
from tests.factories import (
    ItemDateFactory,
    ItemFactory,
    ItemIdentifierFactory,
    ItemNameFactory,
    NameFactory,
)

APP_TEMPLATES_DIR = (
    Path(__file__).resolve().parents[2] / "literature" / "ui" / "templates"
)
TEMPLATES_DIR = APP_TEMPLATES_DIR / "literature" / "ui"
#: Included so the i18n and utility-class guards below also reach the toolbar
#: action components, which live outside ``TEMPLATES_DIR``.
COTTON_ACTIONS_DIR = APP_TEMPLATES_DIR / "cotton" / "page" / "list" / "actions"
#: The components a project uses on its own pages.
COTTON_LITERATURE_DIR = APP_TEMPLATES_DIR / "cotton" / "literature"
TEMPLATE_PATHS = (
    sorted(TEMPLATES_DIR.glob("*.html"))
    + sorted(COTTON_ACTIONS_DIR.glob("*.html"))
    + sorted(COTTON_LITERATURE_DIR.glob("*.html"))
)
PASSTHROUGH_BASE = APP_TEMPLATES_DIR / "base.html"


class TestTheBaseTemplateIsNoLongerOurs:
    # django-mvp 0.18 ships its own base.html; these keep the guarantee, not the file.

    def test_the_app_ships_no_base_template_of_its_own(self):
        assert not PASSTHROUGH_BASE.exists()

    def test_the_packaged_chain_resolves_for_a_project_with_no_base_template(
        self, settings
    ):
        settings.TEMPLATES = [{**settings.TEMPLATES[0], "DIRS": []}]
        from django.template.loader import get_template

        origin = get_template("base.html").origin.name
        assert origin.endswith("mvp/templates/base.html")

    def test_a_project_template_directory_still_wins(self, tmp_path, settings):
        # The politeness guarantee, unchanged: DIRS is searched before any app,
        # so a project that has its own base.html keeps it.
        (tmp_path / "base.html").write_text("the project's own shell")
        settings.TEMPLATES = [
            {**settings.TEMPLATES[0], "DIRS": [str(tmp_path)]},
        ]
        from django.template.loader import get_template

        assert get_template("base.html").origin.name == str(tmp_path / "base.html")


class TestPackagedChain:
    def test_the_reference_page_extends_the_packaged_detail_template(self):
        source = (TEMPLATES_DIR / "item_detail.html").read_text()
        assert '{% extends "detail_view.html" %}' in source

    def test_no_page_template_of_our_own_stands_in_for_a_packaged_one(self):
        # The card list and the contributor page render through
        # ``list_view.html``; neither has a template here.
        assert not (TEMPLATES_DIR / "base.html").exists()
        assert not (TEMPLATES_DIR / "item_list.html").exists()
        assert not (TEMPLATES_DIR / "contributor_detail.html").exists()


# Utility-class allowlist.
#
# django-mvp's own ``docs/utility-classes.md`` is the source of truth, but it
# ships only in the django-mvp *source repo*, not inside the installed
# package: ``pathlib.Path(mvp.__path__[0]).rglob('*utility*')`` returns
# nothing for django-mvp 0.17.0, so this test module cannot read it at test
# time. The allowlist below is that document's content, reproduced as data,
# read at django-mvp 0.17.0. Re-check it by hand against
# ``docs/utility-classes.md`` whenever django-mvp is bumped past 0.17.0.
#
# django-accounts-center shipping two workaround CSS rules is the evidence
# this mechanical check earns its keep: a class token outside the documented
# set can render correctly in dev against whatever stylesheet happens to be
# on disk and then break for a host that only ships the packaged one.

SCALE = ["0", "1", "2", "3", "4", "5", "6", "8", "10", "12"]


def expand(pattern: str) -> list[str]:
    """Expand every ``{a,b,c}`` or ``{1..12}`` group in a utility-classes.md pattern.

    A pattern with no group is already a literal class name.
    """
    match = re.search(r"\{([^{}]+)\}", pattern)
    if not match:
        return [pattern]
    options: list[str] = []
    for part in match.group(1).split(","):
        part = part.strip()
        if ".." in part:
            low, high = part.split("..")
            options.extend(str(n) for n in range(int(low), int(high) + 1))
        else:
            options.append(part)
    expanded: list[str] = []
    for option in options:
        expanded.extend(
            expand(pattern[: match.start()] + option + pattern[match.end() :])
        )
    return expanded


def expand_all(patterns: list[str]) -> set[str]:
    tokens: set[str] = set()
    for pattern in patterns:
        tokens.update(expand(pattern))
    return tokens


def scaled(prefixes: list[str], scale: list[str]) -> set[str]:
    return {f"{prefix}-{n}" for prefix in prefixes for n in scale}


# utility-classes.md's "responsive groups": bare, or behind md:/lg:/xl:.
RESPONSIVE_GROUP_PATTERNS = [
    "block",
    "inline-block",
    "inline",
    "flex",
    "inline-flex",
    "grid",
    "hidden",
    "flex-row",
    "flex-col",
    "flex-wrap",
    "flex-nowrap",
    "flex-1",
    "flex-auto",
    "flex-none",
    "grow",
    "grow-0",
    "shrink",
    "shrink-0",
    "items-{start,center,end,baseline,stretch}",
    "justify-{start,center,end,between,around,evenly}",
    "content-{start,center,end,between,around,evenly}",
    "self-{auto,start,center,end,stretch}",
    "grid-cols-{1..12}",
    "col-span-{1..12,full}",
    "w-{auto,full,screen,min,max,fit,1/2,1/3,2/3,1/4,3/4}",
    "h-{auto,full,screen,min,max,fit}",
    "max-w-{xs,sm,md,lg,xl,2xl,3xl,4xl,5xl,6xl,7xl,full,none,prose}",
    "min-w-{0,full}",
    "max-h-{full,screen}",
    "min-h-{0,full,screen}",
    "text-{left,center,right,justify}",
    "text-{xs,sm,base,lg,xl,2xl,3xl,4xl,5xl,6xl}",
    "static",
    "relative",
    "absolute",
    "fixed",
    "sticky",
    "inset-0",
    "inset-x-0",
    "inset-y-0",
    "top-{0,auto}",
    "right-{0,auto}",
    "bottom-{0,auto}",
    "left-{0,auto}",
    "overflow-{auto,hidden,visible,scroll}",
    "overflow-x-auto",
    "overflow-y-auto",
]

RESPONSIVE_ALLOWED = (
    expand_all(RESPONSIVE_GROUP_PATTERNS)
    | scaled(["gap", "gap-x", "gap-y"], SCALE)
    | scaled(["p", "px", "py", "pt", "pr", "pb", "pl"], SCALE)
    | scaled(["m", "mx", "my", "mt", "mr", "mb", "ml"], SCALE)
    | {"m-auto", "mx-auto", "my-auto"}
    # Not in utility-classes.md, but django-mvp's own table_view.html and
    # list_view.html push their toolbar actions to the end of the row with it,
    # so its prebuilt stylesheet carries both ms-auto and md:ms-auto.
    # item_table_page.html redraws that row.
    | {"ms-auto"}
)

# utility-classes.md's "base-only groups": never behind a responsive prefix.
BASE_ONLY_PATTERNS = [
    "z-{0,10,20,30,40,50,auto}",
    "border",
    "border-0",
    "border-2",
    "border-4",
    "border-8",
    "border-t",
    "border-r",
    "border-b",
    "border-l",
    "rounded-{none,sm,md,lg,xl,2xl,3xl,full}",
    "rounded-{t,r,b,l}-{sm,md,lg,xl,full}",
    "opacity-{0,25,50,75,100}",
    "font-{sans,serif,mono}",
    "font-{light,normal,medium,semibold,bold,extrabold}",
    "leading-{none,tight,snug,normal,relaxed,loose}",
    "tracking-{tight,normal,wide}",
    "truncate",
    "whitespace-nowrap",
    "break-words",
    "italic",
    "uppercase",
    "lowercase",
    "capitalize",
    "underline",
    "no-underline",
    "cursor-{pointer,not-allowed,default}",
    "transition",
    "select-none",
    "pointer-events-none",
    "align-middle",
    "duration-{150,200,300}",
    "object-{cover,contain,fill}",
    "list-{none,disc,decimal}",
]

BASE_ONLY_ALLOWED = expand_all(BASE_ONLY_PATTERNS)

# utility-classes.md's colour utilities: bg-/text-/border- over the daisyUI
# semantic palette, base only — plus hover:/focus-visible: state variants.
PALETTE = [
    "primary",
    "secondary",
    "accent",
    "neutral",
    "info",
    "success",
    "warning",
    "error",
    "primary-content",
    "secondary-content",
    "accent-content",
    "neutral-content",
    "info-content",
    "success-content",
    "warning-content",
    "error-content",
    "base-100",
    "base-200",
    "base-300",
    "base-content",
]

COLOUR_ALLOWED = {
    f"{prefix}-{colour}" for prefix in ("bg", "text", "border") for colour in PALETTE
}
STATE_ALLOWED = COLOUR_ALLOWED | {"opacity-75", "opacity-100", "underline"}

RESPONSIVE_PREFIXES = ("md:", "lg:", "xl:")
STATE_PREFIXES = ("hover:", "focus-visible:")
REJECTED_PREFIXES = ("sm:", "2xl:")

CLASS_ATTR_RE = re.compile(r'(?<!:)\bclass="([^"]*)"')
TEMPLATE_EXPR_RE = re.compile(r"\{\{.*?\}\}|\{%.*?%\}", re.DOTALL)


def extract_class_tokens(source: str) -> list[str]:
    """Return every token inside a literal ``class="..."`` attribute in ``source``.

    Cotton's bound ``:class`` and other component parameters do not match. Template expressions
    are stripped before splitting, so ``{{ page.class }}`` cannot leak words as class names.
    """
    tokens: list[str] = []
    for match in CLASS_ATTR_RE.finditer(source):
        value = TEMPLATE_EXPR_RE.sub(" ", match.group(1))
        tokens.extend(value.split())
    return tokens


def is_allowed_utility_class(token: str) -> bool:
    """Return whether django-mvp's utility-classes.md documents ``token``.

    Arbitrary values and opacity modifiers fail by absence. ``sm:`` and ``2xl:`` are rejected
    outright, so a valid name behind a disallowed prefix cannot slip through.
    """
    if "{{" in token or "{%" in token:
        return False
    if token.startswith(REJECTED_PREFIXES):
        return False
    for prefix in STATE_PREFIXES:
        if token.startswith(prefix):
            return token[len(prefix) :] in STATE_ALLOWED
    for prefix in RESPONSIVE_PREFIXES:
        if token.startswith(prefix):
            return token[len(prefix) :] in RESPONSIVE_ALLOWED
    return (
        token in RESPONSIVE_ALLOWED
        or token in BASE_ONLY_ALLOWED
        or token in COLOUR_ALLOWED
    )


class TestUtilityClassAllowlist:
    @pytest.mark.parametrize("template_path", TEMPLATE_PATHS, ids=lambda p: p.name)
    def test_every_class_token_is_allowlisted(self, template_path):
        tokens = extract_class_tokens(template_path.read_text())
        disallowed = [token for token in tokens if not is_allowed_utility_class(token)]
        assert not disallowed, (
            f"{template_path.name}: non-allowlisted class token(s) {disallowed}"
        )

    @pytest.mark.parametrize(
        "token",
        [
            "w-[37px]",
            "text-base-content/60",
            "sm:flex",
            "2xl:hidden",
            "sm:hidden",
            "2xl:block",
        ],
    )
    def test_rejects_arbitrary_values_opacity_modifiers_and_disallowed_prefixes(
        self, token
    ):
        assert not is_allowed_utility_class(token)

    @pytest.mark.parametrize(
        "token",
        [
            "flex",
            "py-4",
            "text-lg",
            "font-semibold",
            "md:flex",
            "lg:grid-cols-6",
            "xl:hidden",
            "text-primary",
            "hover:text-primary",
            "focus-visible:opacity-75",
        ],
    )
    def test_accepts_documented_utilities_and_their_allowed_prefixes(self, token):
        assert is_allowed_utility_class(token)


# i18n guard.
#
# Every literal string a reader sees in a shipped template must be inside
# {% translate %} or {% blocktranslate %}. Two places a reader can see one:
# a text node between HTML tags, and a component attribute that carries
# content rather than configuration. The second needs the same kind of
# named list the class guard above needs, because ``title="Contributors"``
# is prose and ``size="sm"`` is not, and nothing in the markup distinguishes
# them. READER_FACING_ATTRIBUTES is that list. Add to it when a component
# this app uses grows another content attribute.

#: Attributes whose value is shown to a reader as language. Everything else —
#: ``size``, ``cols``, ``md``, ``gap``, ``muted``, ``name`` — configures a
#: component and is not translated.
READER_FACING_ATTRIBUTES = (
    "title",
    "label",
    "text",
    "heading",
    "message",
    "placeholder",
    "alt",
)

BLOCKTRANSLATE_RE = re.compile(
    r"\{%\s*blocktranslate\b.*?%\}.*?\{%\s*endblocktranslate\s*%\}", re.DOTALL
)
TRANSLATE_TAG_RE = re.compile(r"\{%\s*trans(?:late)?\s+[\"'][^\"']*[\"']\s*%\}")
#: ``{# … #}`` is a SINGLE-LINE comment. Django's own lexer compiles
#: ``({%.*?%}|{{.*?}}|{#.*?#})`` without ``re.DOTALL``, so a ``{#`` whose ``#}``
#: sits on a later line is never tokenised as a comment and the whole block is
#: emitted to the page as literal text. This regex deliberately mirrors that —
#: matching with ``re.DOTALL`` here is what let four multi-line ``{# … #}``
#: blocks ship and render to readers while this guard stayed green, because the
#: guard held the same wrong belief the templates did.
DJANGO_COMMENT_RE = re.compile(r"\{#[^\n]*?#\}")
#: ``{% comment %}…{% endcomment %}`` is the multi-line form and is genuinely
#: never rendered. Stripped before the generic tag regex, which would otherwise
#: remove the two tags and leave their prose behind as residue.
DJANGO_BLOCK_COMMENT_RE = re.compile(
    r"\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}",
    re.DOTALL,
)
DJANGO_TAG_RE = re.compile(r"\{%.*?%\}", re.DOTALL)
DJANGO_VAR_RE = re.compile(r"\{\{.*?\}\}", re.DOTALL)
HTML_TAG_RE = re.compile(r"<[^>]*>", re.DOTALL)
HTML_ENTITY_RE = re.compile(r"&[#a-zA-Z0-9]+;")
LETTER_RE = re.compile(r"[A-Za-z]")
READER_ATTRIBUTE_RE = re.compile(
    r"\b(?:" + "|".join(READER_FACING_ATTRIBUTES) + r")\s*=\s*\"([^\"]*)\"",
)


def reader_visible_residue(source: str) -> str:
    """Return what of ``source`` a reader would see as text, untranslated.

    Comments go first, then translated spans, then other template machinery, then HTML tags and
    entities. A multi-line ``{# … #}`` is not a Django comment, so its prose survives here, as it
    does on the page.
    """
    text = DJANGO_BLOCK_COMMENT_RE.sub(" ", source)
    text = DJANGO_COMMENT_RE.sub(" ", text)
    text = BLOCKTRANSLATE_RE.sub(" ", text)
    text = TRANSLATE_TAG_RE.sub(" ", text)
    text = DJANGO_TAG_RE.sub(" ", text)
    text = DJANGO_VAR_RE.sub(" ", text)
    text = HTML_TAG_RE.sub(" ", text)
    text = HTML_ENTITY_RE.sub(" ", text)
    return text


def unwrapped_reader_attributes(source: str) -> list[str]:
    """Return reader-facing attribute values that still read as language.

    Template machinery is stripped first, so a value built from ``{% translate %}`` or a variable
    leaves nothing behind.
    """
    text = BLOCKTRANSLATE_RE.sub(" ", source)
    text = TRANSLATE_TAG_RE.sub(" ", text)
    text = DJANGO_TAG_RE.sub(" ", text)
    text = DJANGO_VAR_RE.sub(" ", text)
    return [
        value for value in READER_ATTRIBUTE_RE.findall(text) if LETTER_RE.search(value)
    ]


def has_unwrapped_reader_text(source: str) -> bool:
    """Return whether any letter survives :func:`reader_visible_residue`.

    Separators and entities carry no letters, so they pass without being listed.
    """
    return bool(LETTER_RE.search(reader_visible_residue(source)))


class TestI18nGuard:
    @pytest.mark.parametrize("template_path", TEMPLATE_PATHS, ids=lambda p: p.name)
    def test_no_unwrapped_reader_text(self, template_path):
        source = template_path.read_text()
        residue = reader_visible_residue(source)
        assert not has_unwrapped_reader_text(source), (
            f"{template_path.name}: literal reader-facing text outside "
            f"{{% translate %}}/{{% blocktranslate %}}: {residue!r}"
        )

    def test_detects_a_bare_literal_reader_string(self):
        assert has_unwrapped_reader_text("<c-text>Showing results</c-text>")

    def test_accepts_the_same_string_wrapped_in_translate(self):
        assert not has_unwrapped_reader_text(
            '<c-text>{% translate "Showing results" %}</c-text>'
        )

    def test_ignores_prose_inside_a_template_comment(self):
        assert not has_unwrapped_reader_text(
            "{# a note to the next reader of this file #}"
        )

    def test_ignores_prose_inside_a_block_comment(self):
        assert not has_unwrapped_reader_text(
            "{% comment %}\n  a note\n  over several lines\n{% endcomment %}"
        )

    def test_detects_prose_in_a_multiline_single_line_comment(self):
        # Django's lexer has no re.DOTALL, so this is not a comment at all: the
        # whole block reaches the page as literal text. Four of these shipped and
        # rendered planning notes and a paragraph about date precision next to
        # the reader's data. The guard missed them because it stripped `{# … #}`
        # with re.DOTALL, believing what the templates believed.
        assert has_unwrapped_reader_text("{# a note\n   spanning two lines #}")

    def test_accepts_the_same_string_wrapped_in_blocktranslate(self):
        assert not has_unwrapped_reader_text(
            "<c-text>{% blocktranslate %}Showing results{% endblocktranslate %}</c-text>"
        )

    def test_accepts_translate_used_inside_an_attribute_value(self):
        assert not has_unwrapped_reader_text(
            '<c-section title="{% translate "Dates" %}">'
        )

    @pytest.mark.parametrize(
        "fragment",
        [
            "{{ group.grouper }}:",
            "{% if not forloop.last %}, {% endif %}",
            "&middot;",
            "&ndash;",
            "   \n   ",
            "",
        ],
    )
    def test_colon_comma_entities_and_whitespace_do_not_trip_it(self, fragment):
        assert not has_unwrapped_reader_text(fragment)

    @pytest.mark.parametrize("template_path", TEMPLATE_PATHS, ids=lambda p: p.name)
    def test_no_unwrapped_reader_facing_attribute(self, template_path):
        found = unwrapped_reader_attributes(template_path.read_text())
        assert not found, (
            f"{template_path.name}: reader-facing attribute value outside "
            f"{{% translate %}}/{{% blocktranslate %}}: {found!r}"
        )

    def test_detects_a_hard_coded_reader_facing_attribute(self):
        assert unwrapped_reader_attributes('<c-section title="Contributors">') == [
            "Contributors"
        ]

    def test_accepts_a_reader_facing_attribute_built_from_translate(self):
        assert (
            unwrapped_reader_attributes(
                '<c-section title="{% translate "Contributors" %}">'
            )
            == []
        )

    def test_accepts_a_reader_facing_attribute_built_from_a_variable(self):
        assert unwrapped_reader_attributes('<c-data-field label="{{ label }}" />') == []

    def test_ignores_configuration_attributes(self):
        assert (
            unwrapped_reader_attributes(
                '<c-text size="sm" muted><c-grid cols="1" md="2" gap="4">'
            )
            == []
        )


# ---------------------------------------------------------------------------
# The import pages themselves.
# ---------------------------------------------------------------------------

#: A RIS record missing its own ``TY`` tag — the format's own documented
#: ``EntryError`` (``literature/importers/ris.py``), reused here from
#: ``tests/test_ui/test_views.py``'s own fixture so the report page under
#: test always carries at least one row.
IMPORT_RIS_FIXTURE = (
    "TY  - JOUR\nAU  - Doe, Jane\nTI  - A Working RIS Reference\nPY  - 2020\nER  -\n"
)


class TestImportFormPage:
    def test_the_form_is_multipart(self, client, db):
        content = client.get(reverse("literature:item-import")).content.decode()
        assert 'enctype="multipart/form-data"' in content

    def test_carries_a_file_control(self, client, db):
        content = client.get(reverse("literature:item-import")).content.decode()
        assert 'type="file"' in content


class TestImportReportPage:
    def _report_content(self, client):
        upload = SimpleUploadedFile("import.ris", IMPORT_RIS_FIXTURE.encode())
        response = client.post(
            reverse("literature:item-import"),
            {"format": "ris", "file": upload, "skip_preview": "on"},
        )
        return response.content.decode()

    def test_carries_the_counts(self, client, db):
        content = self._report_content(client)
        assert "1 created" in content

    def test_carries_a_link_back_to_the_catalogue(self, client, db):
        content = self._report_content(client)
        assert f'href="{reverse("literature:item-list")}"' in content

    def test_carries_no_import_form_of_its_own(self, client, db):
        # The upload form lives on the preview page, not above the results.
        content = self._report_content(client)
        assert 'type="file"' not in content

    def test_carries_a_second_button_leading_to_an_empty_import_form(self, client, db):
        content = self._report_content(client)
        assert f'href="{reverse("literature:item-import")}"' in content


class TestOutcomeFilter:
    def _preview_content(self, client):
        upload = SimpleUploadedFile("import.ris", IMPORT_RIS_FIXTURE.encode())
        client.post(
            reverse("literature:item-import"), {"format": "ris", "file": upload}
        )
        return client.get(reverse("literature:item-import-preview")).content.decode()

    def _filter_markup(self, content):
        start = content.index('class="filter')
        end = content.index("</div>", start)
        return content[start:end]

    def _controls(self, content):
        """Each radio in the filter, as its own chunk of markup."""
        return [
            "<input" + chunk
            for chunk in self._filter_markup(content).split("<input")[1:]
        ]

    def test_one_control_per_outcome_plus_a_way_back_to_all(self, client, db):
        markup = self._filter_markup(self._preview_content(client))
        assert markup.count('type="radio"') == 4  # All, created, skipped, failed

    def test_each_control_is_labelled_with_its_outcomes_own_label(self, client, db):
        controls = self._controls(self._preview_content(client))
        for outcome in OutcomeColumn.VARIANTS:
            control = next(c for c in controls if f'value="{outcome.value}"' in c)
            assert f'aria-label="{outcome.label}"' in control
        reset = next(c for c in controls if "filter-reset" in c)
        assert re.search(r'aria-label="[^"]+"', reset)

    def test_it_carries_no_form_action_and_no_link(self, client, db):
        markup = self._filter_markup(self._preview_content(client))
        assert "<form" not in markup
        assert "<a " not in markup

    def test_the_counts_above_the_table_describe_the_whole_file_not_the_filter(
        self, client, db
    ):
        # The counts are rendered from ``report`` directly and sit
        # outside the filter's own x-data scope, so they read the same
        # whatever the table is narrowed to (proved here by their absence of
        # any Alpine binding at all, since the Django test client renders
        # markup rather than running Alpine).
        content = self._preview_content(client)
        counts_index = content.index("1 created")
        counts_line = content[max(counts_index - 200, 0) : counts_index + 50]
        assert "outcome" not in counts_line
        assert "x-" not in counts_line


class TestImportPreviewTemplate:
    def _preview(self, client, filename="import.ris", format_name="ris", content=None):
        upload = SimpleUploadedFile(filename, (content or IMPORT_RIS_FIXTURE).encode())
        client.post(
            reverse("literature:item-import"), {"format": format_name, "file": upload}
        )
        return client.get(reverse("literature:item-import-preview"))

    def test_carries_no_import_form(self, client, db):
        content = self._preview(client).content.decode()
        assert 'type="file"' not in content

    def test_a_warning_appears_above_the_table_when_an_entry_was_skipped_or_failed(
        self, client, db
    ):
        response = self._preview(
            client, content="AU  - Roe, Jan\nT1  - No Reference Type\nER  -\n"
        )
        content = response.content.decode()
        table_index = content.index("<table")
        warning_index = content.index("alert-warning")
        assert warning_index < table_index

    def test_no_warning_when_every_entry_was_created(self, client, db):
        content = self._preview(client).content.decode()
        assert "alert-warning" not in content

    def test_the_foot_carries_exactly_three_controls_in_one_row(self, client, db):
        content = self._preview(client).content.decode()
        # <c-group> renders to this literal opening class, and this page's
        # footer is the only place it appears after the table.
        footer_index = content.rindex('class="flex flex-col items-stretch')
        footer = content[footer_index:]
        assert footer.count("<a ") == 1  # back to the catalogue
        assert footer.count("<form") == 2  # restart, confirm
        assert reverse("literature:item-list") in footer
        assert f'action="{reverse("literature:item-import-restart")}"' in footer
        assert f'action="{reverse("literature:item-import-confirm")}"' in footer

    def test_a_file_the_format_cannot_read_offers_no_confirmation(self, client, db):
        # Confirming would create nothing, so the control that would
        # carry it out is not offered. The reader is left with restart and the
        # way back to the catalogue.
        response = self._preview(
            client, filename="wrong-format.bib", format_name="bibtex"
        )
        content = response.content.decode()
        assert response.context["report"].created == 0
        assert f'action="{reverse("literature:item-import-confirm")}"' not in content
        assert f'action="{reverse("literature:item-import-restart")}"' in content


class TestImportFormPageFieldErrors:
    def test_a_missing_files_reason_renders_beside_the_file_field(self, client, db):
        content = client.post(
            reverse("literature:item-import"), {"format": "bibtex"}
        ).content.decode()
        assert 'id="id_file_error"' in content

    def test_a_missing_formats_reason_renders_beside_the_format_field(self, client, db):
        upload = SimpleUploadedFile("x.bib", b"@article{x, title={T}}")
        content = client.post(
            reverse("literature:item-import"), {"file": upload}
        ).content.decode()
        assert 'id="id_format_error"' in content


def render_reference(item, **attrs):
    """Render ``<c-literature.item>`` for ``item`` with ``attrs``, as a project would."""
    return render_component(
        RequestFactory().get("/"), "literature.item", item=item, **attrs
    )


def credit(item, role, count):
    """Credit ``count`` new names on ``item`` in ``role``, in order, and return them."""
    return [
        ItemNameFactory(
            item=item, role=role, name=NameFactory(family=f"Family{n:02}")
        ).name
        for n in range(count)
    ]


@pytest.mark.django_db
class TestReferenceComponent:
    def test_the_title_links_to_the_reference_page(self):
        item = ItemFactory(title="A Linked Reference")

        html = render_reference(item)

        assert f'href="{item.get_absolute_url()}"' in html
        assert "A Linked Reference" in html

    def test_an_item_with_no_title_shows_its_citation_key(self):
        html = render_reference(ItemFactory(title="", citation_key="Untitled2026"))

        assert "Untitled2026" in html

    def test_href_replaces_the_title_link(self):
        item = ItemFactory()

        html = render_reference(item, href="/datasets/7/")

        assert 'href="/datasets/7/"' in html
        assert f'href="{item.get_absolute_url()}"' not in html

    def test_without_links_it_renders_where_the_catalogue_is_not_mounted(
        self, settings
    ):
        settings.ROOT_URLCONF = "tests.urls_core"
        item = ItemFactory(title="Unlinked Reference")
        credit(item, NameRole.AUTHOR, 1)

        html = render_reference(item, link=False)

        assert "Unlinked Reference" in html
        assert "<a " not in html

    def test_the_title_heading_level_follows_the_level_attribute(self):
        html = render_reference(ItemFactory(), level=2)

        assert "<h2" in html

    def test_each_author_links_to_their_contributor_page(self):
        item = ItemFactory()
        (author,) = credit(item, NameRole.AUTHOR, 1)

        html = render_reference(item)

        assert (
            reverse("literature:contributor-detail", kwargs={"pk": author.pk}) in html
        )

    def test_ten_authors_are_named_in_full(self):
        item = ItemFactory()
        authors = credit(item, NameRole.AUTHOR, 10)

        html = render_reference(item)

        assert all(author.family in html for author in authors)
        assert "et al." not in html

    def test_beyond_ten_authors_the_rest_are_et_al(self):
        item = ItemFactory()
        authors = credit(item, NameRole.AUTHOR, 11)

        html = render_reference(item)

        assert authors[9].family in html
        assert authors[10].family not in html
        assert "et al." in html

    def test_with_authors_the_editors_are_left_out(self):
        item = ItemFactory()
        credit(item, NameRole.AUTHOR, 1)
        editor = ItemNameFactory(
            item=item, role=NameRole.EDITOR, name=NameFactory(family="Editorson")
        ).name

        html = render_reference(item)

        assert editor.family not in html

    @pytest.mark.parametrize(("count", "mark"), [(1, "(ed.)"), (2, "(eds.)")])
    def test_without_authors_the_editors_stand_in_marked_as_editors(self, count, mark):
        item = ItemFactory()
        editors = credit(item, NameRole.EDITOR, count)

        html = render_reference(item)

        assert all(editor.family in html for editor in editors)
        assert mark in html

    def test_a_journal_article_shows_its_type_year_and_where_it_appeared(self):
        item = ItemFactory(
            type="article-journal",
            container_title="Journal of Tests",
            volume="27",
            issue="3",
            page="379-423",
        )
        ItemDateFactory(
            item=item, date_type=DateType.ISSUED, begin=PartialDate("1948-07")
        )

        html = render_reference(item)

        assert str(item.get_type_display()) in html
        assert "1948" in html
        assert "Journal of Tests" in html
        assert "vol. 27" in html
        assert "no. 3" in html
        assert "pp. 379-423" in html

    def test_without_a_container_the_publisher_is_shown(self):
        item = ItemFactory(type="book", container_title="", publisher="Test Press")

        assert "Test Press" in render_reference(item)

    def test_the_doi_links_to_doi_org(self):
        item = ItemFactory()
        ItemIdentifierFactory(
            item=item, type=IdentifierType.DOI, value="10.1000/xyz123"
        )

        html = render_reference(item)

        assert 'href="https://doi.org/10.1000/xyz123"' in html

    def test_a_reference_with_nothing_but_a_title_renders(self):
        html = render_reference(
            ItemFactory(title="Beowulf", container_title="", publisher="")
        )

        assert "Beowulf" in html
        assert "doi.org" not in html

    def test_the_abstract_is_shown_only_when_asked_for(self):
        item = ItemFactory(abstract="A short abstract of the work.")

        assert "A short abstract" not in render_reference(item)
        assert "A short abstract" in render_reference(item, abstract=True)

    def test_the_default_slot_renders_under_the_reference(self):
        html = render_reference(ItemFactory(), slot="Extra line for the host")

        assert "Extra line for the host" in html

    def test_a_prefetched_item_renders_without_querying(
        self, django_assert_num_queries
    ):
        item = ItemFactory()
        credit(item, NameRole.AUTHOR, 3)
        ItemDateFactory(item=item, date_type=DateType.ISSUED, begin=PartialDate("2020"))
        ItemIdentifierFactory(
            item=item, type=IdentifierType.DOI, value="10.1000/xyz123"
        )
        prefetched = Item.objects.prefetch_related(
            "item_names__name", "item_dates", "item_identifiers"
        ).get(pk=item.pk)

        with django_assert_num_queries(0):
            render_reference(prefetched)
