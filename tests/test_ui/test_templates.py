"""Tests for the templates ``literature.ui`` ships."""

import re
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from literature.ui.tables import OutcomeColumn

APP_TEMPLATES_DIR = (
    Path(__file__).resolve().parents[2] / "literature" / "ui" / "templates"
)
TEMPLATES_DIR = APP_TEMPLATES_DIR / "literature" / "ui"
#: Included so the i18n and utility-class guards below also reach the toolbar
#: action components, which live outside ``TEMPLATES_DIR``.
COTTON_ACTIONS_DIR = APP_TEMPLATES_DIR / "cotton" / "page" / "list" / "actions"
TEMPLATE_PATHS = sorted(TEMPLATES_DIR.glob("*.html")) + sorted(
    COTTON_ACTIONS_DIR.glob("*.html")
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
        # The catalogue list and the contributor page render through
        # ``list_view.html``; neither has a template here.
        # ``item_list_page.html`` (``ItemListView.template_name``) does not
        # contradict this: it ``{% extends "list_view.html" %}`` and
        # overrides only the ``page.actions`` block, a wrapper around the
        # packaged template rather than a replacement of it — the file this
        # test guards against is named ``item_list.html`` (no ``_page``) and
        # would stand in for ``list_view.html`` wholesale, which is a
        # different thing.
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


class TestItemFormPageMarkup:
    def test_the_button_row_passes_the_group_no_variable_it_does_not_declare(
        self, client, db
    ):
        # The same defect this page carried since its own phase: see
        # TestImportReportPage's test of the same name.
        content = client.get(reverse("literature:item-create")).content.decode()
        assert "breakpoint=" not in content


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

    def test_the_back_to_catalogue_button_carries_a_backward_arrow(self, client, db):
        # This page's breadcrumb links to the catalogue too, so the first occurrence of this href is
        # now the breadcrumb's, not the button's — the last one is.
        content = self._report_content(client)
        back_href = f'href="{reverse("literature:item-list")}"'
        back_index = content.rindex(back_href)
        assert "bi-arrow-left" in content[max(back_index - 200, 0) : back_index + 200]

    def test_carries_a_second_button_leading_to_an_empty_import_form(self, client, db):
        content = self._report_content(client)
        assert f'href="{reverse("literature:item-import")}"' in content

    def test_the_button_row_passes_the_group_no_variable_it_does_not_declare(
        self, client, db
    ):
        # ``<c-group>`` declares row, collapse, wrap, class and gap. An
        # attribute it does not declare is not ignored: Cotton writes it
        # through to the rendered <div>, where it is invalid HTML and lays
        # nothing out. Asserted on the rendered page rather than on the
        # template so the check reads what a browser would receive.
        assert "breakpoint=" not in self._report_content(client)


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

    def test_every_control_is_small(self, client, db):
        markup = self._filter_markup(self._preview_content(client))
        assert markup.count('type="radio"') == markup.count("btn-sm")

    def test_each_outcome_control_carries_the_same_tone_as_that_outcome_s_badge(
        self, client, db
    ):
        # The control and the badge for one outcome must read as the same
        # thing. Asserted against the badge's own mapping rather than against
        # tone names written out here, so restyling the badges moves the
        # filter with them and cannot leave the two disagreeing.
        controls = self._controls(self._preview_content(client))
        for outcome, variant in OutcomeColumn.VARIANTS.items():
            control = next(c for c in controls if f'value="{outcome.value}"' in c)
            assert f"btn-{variant}" in control, (
                f"{outcome.value} control is not toned as its badge"
            )

    def test_the_way_back_to_all_carries_no_outcome_tone(self, client, db):
        controls = self._controls(self._preview_content(client))
        reset = next(c for c in controls if "filter-reset" in c)
        for variant in OutcomeColumn.VARIANTS.values():
            assert f"btn-{variant}" not in reset


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

    def test_the_filter_component_sits_above_the_table(self, client, db):
        content = self._preview(client).content.decode()
        filter_index = content.index('class="filter')
        table_index = content.index("<table")
        assert filter_index < table_index

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
        assert 'id="error_1_id_file"' in content

    def test_a_missing_formats_reason_renders_beside_the_format_field(self, client, db):
        upload = SimpleUploadedFile("x.bib", b"@article{x, title={T}}")
        content = client.post(
            reverse("literature:item-import"), {"file": upload}
        ).content.decode()
        assert 'id="error_1_id_format"' in content
