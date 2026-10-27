"""The demo guard's assertion script, speaking real HTTP to a running demo server (FS-007, FS-008, FS-009, FS-011, FS-012)."""

# Standard library only and run directly against a live server, not under pytest.
# It knows one address, the catalogue list, and follows links from there: a script
# that built its own URLs would pass over a catalogue whose links are broken.

import html
import http.cookiejar
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from html.parser import HTMLParser
from pathlib import Path

# Beside the seed data: the walk speaks HTTP only, so it cannot ask the app registry (FS-011).
IMPORT_FIXTURE_PATH = Path(__file__).resolve().parent / "seed" / "import-sample.bib"

# DEBUG is on in the demo: an unbounded body would put Django's technical-500 page
# into a public CI log (FS-007).
BODY_EXCERPT_LIMIT = 500

ITEM_LINK_RE = re.compile(r'href="(?P<path>/catalogue/\d+/)"[^>]*>(?P<text>[^<]+)<')
CONTRIBUTOR_LINK_RE = re.compile(
    r'href="(?P<path>/catalogue/contributors/\d+/)"[^>]*>(?P<text>[^<]+)<'
)

# The toolbar controls: a single choice travels in a hidden input joined to the filter
# form by `form="filterForm"`, so these look for the named control, not ``form_fields``.
SEARCH_INPUT_RE = re.compile(r'<input[^>]+type="search"[^>]+name="q"')


def filter_control_re(name: str) -> re.Pattern[str]:
    """Match the toolbar's control named ``name``.

    Args:
        name: The control's ``name`` attribute.

    Returns:
        The compiled pattern.
    """
    return re.compile(rf'<(?:select|input)[^>]+name="{name}"')


# Matches the second-page link, which joins other parameters with `&amp;`. The captured
# group is raw HTML: unescape it before building a URL (FS-010).
SECOND_PAGE_LINK_RE = re.compile(
    r'href="(?P<query>\?(?:[^"]*&(?:amp;)?)?page=2(?:&(?:amp;)?[^"]*)?)"'
)

# The Add, Edit, Delete and Import actions (FS-008, FS-011). They capture the address
# only: the button's text sits behind an icon element, not right after the href.
CREATE_LINK_RE = re.compile(r'href="(?P<path>/catalogue/add/)"')
EDIT_LINK_RE = re.compile(r'href="(?P<path>/catalogue/\d+/update/)"')
DELETE_LINK_RE = re.compile(r'href="(?P<path>/catalogue/\d+/delete/)"')

IMPORT_LINK_RE = re.compile(r'href="(?P<path>/catalogue/import/)"')

# The catalogue links to no sign-in page, so the walk signs in through the admin as the
# account ``seed_demo`` leaves behind.
SIGN_IN_PATH = "/admin/login/"
EDITOR_USERNAME = "editor.user"
EDITOR_PASSWORD = "password"  # noqa: S105 — the demo's published login, not a secret

# Unlike the patterns above, these match a <form>'s action: confirming and restarting
# an import are POSTs, never links (FS-011).
CONFIRM_IMPORT_RE = re.compile(
    r'<form[^>]+action="(?P<path>/catalogue/import/confirm/)"'
)

RESTART_IMPORT_RE = re.compile(
    r'<form[^>]+action="(?P<path>/catalogue/import/restart/)"'
)


class FormFieldParser(HTMLParser):
    """Collect field name to current value for the first ``<form>`` on a page (FS-008).

    Walks ``input``, ``select``/``option`` and ``textarea`` tags as a browser's form
    submission would: an element with no ``name`` contributes nothing, a ``select``'s
    value is its ``selected`` option or else its first, and a ``textarea``'s value is
    its text. A caller can then post the whole form back with one field changed, as
    posting only that field would blank the rest.
    """

    def __init__(self):
        super().__init__()
        self.fields: dict[str, str] = {}
        self.in_form = False
        # Set once the first form closes, so a second form contributes nothing.
        self.first_form_done = False
        self.current_select: str | None = None
        self.selects_with_an_option_seen: set[str] = set()
        self.current_textarea: str | None = None
        self.textarea_chunks: list[str] = []

    def handle_starttag(self, tag, attrs):
        """Record the field this start tag contributes, if any.

        Args:
            tag: The tag name.
            attrs: The tag's ``(name, value)`` attribute pairs.
        """
        attr_dict = dict(attrs)
        if tag == "form":
            if not self.first_form_done:
                self.in_form = True
            return
        if not self.in_form:
            return

        if tag == "input":
            name = attr_dict.get("name")
            if not name:
                return
            input_type = attr_dict.get("type", "text")
            if input_type in ("submit", "button", "reset", "image"):
                return
            if input_type in ("checkbox", "radio"):
                if "checked" in attr_dict:
                    self.fields[name] = attr_dict.get("value", "on")
                return
            self.fields[name] = attr_dict.get("value", "")
        elif tag == "select":
            self.current_select = attr_dict.get("name")
            if self.current_select:
                self.fields.setdefault(self.current_select, "")
        elif tag == "option":
            if self.current_select is None:
                return
            value = attr_dict.get("value", "")
            # As in a browser: the first option is the fallback, a later `selected` one wins.
            if self.current_select not in self.selects_with_an_option_seen:
                self.fields[self.current_select] = value
                self.selects_with_an_option_seen.add(self.current_select)
            if "selected" in attr_dict:
                self.fields[self.current_select] = value
        elif tag == "textarea":
            self.current_textarea = attr_dict.get("name")
            self.textarea_chunks = []
            if self.current_textarea:
                self.fields.setdefault(self.current_textarea, "")

    def handle_endtag(self, tag):
        """Close off tracking for the tag this end tag closes.

        Args:
            tag: The tag name.
        """
        if tag == "form":
            if self.in_form:
                self.first_form_done = True
            self.in_form = False
        elif tag == "select":
            self.current_select = None
        elif tag == "textarea":
            if self.current_textarea:
                value = "".join(self.textarea_chunks)
                # HTML ignores one newline right after <textarea>, which Django's widget
                # writes; keeping it would grow every round-tripped value.
                if value.startswith("\n"):
                    value = value[1:]
                self.fields[self.current_textarea] = value
            self.current_textarea = None
            self.textarea_chunks = []

    def handle_data(self, data):
        """Accumulate text content while inside a ``textarea``.

        Args:
            data: A chunk of text.
        """
        if self.current_textarea is not None:
            self.textarea_chunks.append(data)


def form_fields(body: str) -> dict[str, str]:
    """Return the name to value pairs the first ``<form>`` in ``body`` would post (FS-008).

    Args:
        body: The page's HTML.

    Returns:
        The form's fields.
    """
    parser = FormFieldParser()
    parser.feed(body)
    return parser.fields


def encode_multipart(
    fields: dict[str, str], files: dict[str, tuple[str, bytes, str]]
) -> tuple[bytes, str]:
    """Build a ``multipart/form-data`` body and its ``Content-Type`` header value (FS-011).

    A second encoder beside ``post``'s urlencoding, as a file cannot ride in a
    urlencoded body and only the import form carries one.

    Args:
        fields: Ordinary form fields, name to value.
        files: File fields, name to ``(filename, content, content_type)``.

    Returns:
        The encoded body and a ``Content-Type`` value carrying the boundary.
    """
    boundary = uuid.uuid4().hex
    lines: list[bytes] = []
    for name, value in fields.items():
        lines.append(f"--{boundary}".encode())
        lines.append(f'Content-Disposition: form-data; name="{name}"'.encode())
        lines.append(b"")
        lines.append(value.encode())
    for name, (filename, content, content_type) in files.items():
        lines.append(f"--{boundary}".encode())
        lines.append(
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"'.encode()
        )
        lines.append(f"Content-Type: {content_type}".encode())
        lines.append(b"")
        lines.append(content)
    lines.append(f"--{boundary}--".encode())
    lines.append(b"")
    return b"\r\n".join(lines), f"multipart/form-data; boundary={boundary}"


class SmokeCheckFailed(Exception):
    """Report a failed check with its URL, status and a bounded body excerpt (FS-007)."""


class DemoWalk:
    """Walk the demo from its catalogue list, following links only (FS-007).

    One cookie-carrying opener serves every request, as a form's CSRF cookie set on
    GET must travel with the POST back (FS-008).

    Args:
        base_url: The running demo's address.
    """

    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )

    def run(self):
        """Walk every check in order, starting from the catalogue list."""
        list_url = f"{self.base_url}/catalogue/"
        list_body = self.get(list_url)
        item_links = ITEM_LINK_RE.findall(list_body)
        if not item_links:
            self.fail(
                list_url,
                200,
                "no reference link on the catalogue list — the seed did not load",
                list_body,
            )

        self.walk_narrowed_catalogue(list_url, list_body)
        self.walk_to_contributor(item_links)

        # A visitor who is not signed in is offered no way to write.
        if CREATE_LINK_RE.search(list_body) or IMPORT_LINK_RE.search(list_body):
            self.fail(
                list_url,
                200,
                "offers Add or Import to a visitor not signed in",
                list_body,
            )
        self.sign_in()
        list_body = self.get(list_url)

        self.walk_write_pass(list_url, list_body)
        self.walk_related_rows(list_url, list_body)
        # Last (FS-011): it leaves references behind, which would break
        # walk_narrowed_catalogue's membership assertions on a second run.
        self.walk_import(list_url, list_body)

    def walk_narrowed_catalogue(self, list_url, list_body):
        """Check a search, a filter and a page move over a narrowed result (FS-010).

        Each step submits one query parameter alone, as a browser does when the other
        controls are untouched. Assertions are on the references present and absent,
        never a status code alone.

        Args:
            list_url: The catalogue list's address.
            list_body: The catalogue list's HTML.
        """
        if not all(
            filter_control_re(name).search(list_body) for name in ("type", "language")
        ):
            self.fail(
                list_url,
                200,
                "the catalogue list's filter form carries no type or language control",
                list_body,
            )
        if SEARCH_INPUT_RE.search(list_body) is None:
            self.fail(list_url, 200, "no search box on the catalogue list", list_body)

        # SEARCH_FIELDS includes citation_key, and every seeded key is unique.
        search_url = f"{list_url}?{urllib.parse.urlencode({'q': 'Shannon1948'})}"
        search_body = self.get(search_url)
        if "A Mathematical Theory of Communication" not in search_body:
            self.fail(
                search_url,
                200,
                "searching citation key 'Shannon1948' did not return its own reference",
                search_body,
            )
        if "Attention Is All You Need" in search_body:
            self.fail(
                search_url,
                200,
                "searching citation key 'Shannon1948' also returned an unrelated reference",
                search_body,
            )

        # The seed carries exactly one `dataset` reference.
        filter_url = f"{list_url}?{urllib.parse.urlencode({'type': 'dataset'})}"
        filter_body = self.get(filter_url)
        if "Physical oceanography during POLARSTERN cruise ANT-II/3" not in filter_body:
            self.fail(
                filter_url,
                200,
                "filtering to type=dataset did not return the seed's one dataset reference",
                filter_body,
            )
        if "A Mathematical Theory of Communication" in filter_body:
            self.fail(
                filter_url,
                200,
                "filtering to type=dataset also returned a non-dataset reference",
                filter_body,
            )

        # The seed's dominant language clears the page size, so page 2 of it is real (FS-010).
        narrowed_url = f"{list_url}?{urllib.parse.urlencode({'language': 'en'})}"
        narrowed_body = self.get(narrowed_url)
        if "Cien años de soledad" in narrowed_body:
            self.fail(
                narrowed_url,
                200,
                "filtering to language=en also returned a Spanish-language reference",
                narrowed_body,
            )
        first_page_paths = {path for path, _text in ITEM_LINK_RE.findall(narrowed_body)}
        if not first_page_paths:
            self.fail(
                narrowed_url,
                200,
                "filtering to language=en returned no references at all",
                narrowed_body,
            )

        second_page_match = SECOND_PAGE_LINK_RE.search(narrowed_body)
        if second_page_match is None:
            self.fail(
                narrowed_url,
                200,
                "no second-page link on the language=en narrowed result",
                narrowed_body,
            )
        second_page_url = f"{list_url}{html.unescape(second_page_match.group('query'))}"
        second_page_body = self.get(second_page_url)
        if "Cien años de soledad" in second_page_body:
            self.fail(
                second_page_url,
                200,
                "the language filter was lost on the page move",
                second_page_body,
            )
        second_page_paths = {
            path for path, _text in ITEM_LINK_RE.findall(second_page_body)
        }
        if not second_page_paths:
            self.fail(
                second_page_url,
                200,
                "no reference link on the narrowed result's second page",
                second_page_body,
            )
        if second_page_paths & first_page_paths:
            self.fail(
                second_page_url,
                200,
                "the narrowed result's second page repeats a reference from its first page",
                second_page_body,
            )

    def walk_to_contributor(self, item_links):
        """Follow the list's reference links in order until one has a contributor (FS-007).

        Args:
            item_links: ``(path, title)`` pairs from the catalogue list.
        """
        tried = []
        for path, title in item_links:
            item_url = f"{self.base_url}{path}"
            tried.append(item_url)
            item_body = self.get(item_url)
            if title not in item_body:
                self.fail(
                    item_url,
                    200,
                    f"reference page does not carry the catalogue's title {title!r}",
                    item_body,
                )

            contributor_match = CONTRIBUTOR_LINK_RE.search(item_body)
            if contributor_match is None:
                continue

            contributor_path = contributor_match.group("path")
            contributor_name = contributor_match.group("text")
            contributor_url = f"{self.base_url}{contributor_path}"
            contributor_body = self.get(contributor_url)
            if contributor_name not in contributor_body:
                self.fail(
                    contributor_url,
                    200,
                    f"contributor page does not carry the credited name {contributor_name!r}",
                    contributor_body,
                )
            return

        self.fail(
            self.base_url,
            None,
            f"none of {len(tried)} reference page(s) carried a contributor link: {', '.join(tried)}",
        )

    def walk_write_pass(self, list_url, list_body):
        """Create, correct and remove a reference over HTTP (FS-008).

        Every POST carries the whole rendered form back with only the field the step
        changes: a bare field dict would blank the rest, which is the defect this pass
        exists to catch. Each step asserts the catalogue changed as claimed, never just
        a 200 (docs/adr/0018-a-guard-asserts-on-content-not-on-a-status-code.md).

        Args:
            list_url: The catalogue list's address.
            list_body: The catalogue list's HTML.
        """
        create_match = CREATE_LINK_RE.search(list_body)
        if create_match is None:
            self.fail(list_url, 200, "no Add link on the catalogue list", list_body)
        create_url = f"{self.base_url}{create_match.group('path')}"

        create_form_body = self.get(create_url)
        fields = form_fields(create_form_body)
        title = f"Smoke Test Reference {uuid.uuid4().hex[:8]}"
        citation_key = f"smoke-{uuid.uuid4().hex[:8]}"
        fields["type"] = "book"
        fields["title"] = title
        fields["citation_key"] = citation_key
        detail_body, detail_url = self.post(create_url, create_url, fields)
        item_path = urllib.parse.urlparse(detail_url).path
        if not re.fullmatch(r"/catalogue/\d+/", item_path):
            self.fail(
                detail_url,
                200,
                f"creating a reference did not redirect to its own page (landed on {detail_url})",
                detail_body,
            )
        if title not in detail_body:
            self.fail(
                detail_url,
                200,
                f"created reference's page does not carry its own title {title!r}",
                detail_body,
            )

        list_after_create = self.get(list_url)
        listed_paths = [path for path, _text in ITEM_LINK_RE.findall(list_after_create)]
        if item_path not in listed_paths:
            self.fail(
                list_url,
                200,
                f"catalogue list does not list the just-created reference at {item_path}",
                list_after_create,
            )

        edit_match = EDIT_LINK_RE.search(detail_body)
        if edit_match is None:
            self.fail(
                detail_url,
                200,
                "no Edit link on the created reference's page",
                detail_body,
            )
        edit_url = f"{self.base_url}{edit_match.group('path')}"

        edit_form_body = self.get(edit_url)
        edit_fields = form_fields(edit_form_body)
        corrected_title = f"{title} (corrected)"
        edit_fields["title"] = corrected_title
        updated_body, updated_url = self.post(edit_url, edit_url, edit_fields)
        if urllib.parse.urlparse(updated_url).path != item_path:
            self.fail(
                updated_url,
                200,
                f"correcting a reference did not redirect to its own page (landed on {updated_url})",
                updated_body,
            )
        if corrected_title not in updated_body:
            self.fail(
                updated_url,
                200,
                f"corrected reference's page does not carry the new title {corrected_title!r}",
                updated_body,
            )
        if citation_key not in updated_body:
            self.fail(
                updated_url,
                200,
                f"corrected reference's page lost its citation key {citation_key!r} — "
                "the edit posted a partial form and blanked a field it did not mean to change",
                updated_body,
            )

        delete_match = DELETE_LINK_RE.search(updated_body)
        if delete_match is None:
            self.fail(
                updated_url,
                200,
                "no Delete link on the corrected reference's page",
                updated_body,
            )
        delete_url = f"{self.base_url}{delete_match.group('path')}"

        delete_form_body = self.get(delete_url)
        delete_fields = form_fields(delete_form_body)
        list_after_delete, _final_url = self.post(delete_url, delete_url, delete_fields)
        remaining_paths = [
            path for path, _text in ITEM_LINK_RE.findall(list_after_delete)
        ]
        if item_path in remaining_paths:
            self.fail(
                list_url,
                200,
                f"catalogue list still lists the deleted reference at {item_path}",
                list_after_delete,
            )

    def walk_related_rows(self, list_url, list_body):
        """Credit a contributor, date and identify a reference through its edit form (FS-012).

        Creates and removes its own reference, so a persistent demo database is left
        as found. Each addition is its own POST, so a broken flow is named on its own
        step, and each asserts what the reference's page shows
        (docs/adr/0018-a-guard-asserts-on-content-not-on-a-status-code.md).

        Args:
            list_url: The catalogue list's address.
            list_body: The catalogue list's HTML.
        """
        create_match = CREATE_LINK_RE.search(list_body)
        if create_match is None:
            self.fail(list_url, 200, "no Add link on the catalogue list", list_body)
        create_url = f"{self.base_url}{create_match.group('path')}"

        create_form_body = self.get(create_url)
        fields = form_fields(create_form_body)
        fields["type"] = "book"
        fields["title"] = f"Smoke Test Related Rows {uuid.uuid4().hex[:8]}"
        fields["citation_key"] = f"smoke-related-{uuid.uuid4().hex[:8]}"
        detail_body, detail_url = self.post(create_url, create_url, fields)
        item_path = urllib.parse.urlparse(detail_url).path
        if not re.fullmatch(r"/catalogue/\d+/", item_path):
            self.fail(
                detail_url,
                200,
                f"creating a reference for the related-row walk did not redirect to its own page "
                f"(landed on {detail_url})",
                detail_body,
            )

        edit_match = EDIT_LINK_RE.search(detail_body)
        if edit_match is None:
            self.fail(
                detail_url,
                200,
                "no Edit link on the created reference's page",
                detail_body,
            )
        edit_url = f"{self.base_url}{edit_match.group('path')}"

        contributor_name = f"Smoke Contributor {uuid.uuid4().hex[:6]}"
        contributor_fields = form_fields(self.get(edit_url))
        contributor_fields["contributors-author-0-family"] = contributor_name
        after_contributor_body, landed_url = self.post(
            edit_url, edit_url, contributor_fields
        )
        if urllib.parse.urlparse(landed_url).path != item_path:
            self.fail(
                landed_url,
                200,
                f"crediting a contributor did not redirect to the reference's own page (landed on {landed_url})",
                after_contributor_body,
            )
        if contributor_name not in after_contributor_body:
            self.fail(
                landed_url,
                200,
                f"reference page does not credit the contributor {contributor_name!r} after saving",
                after_contributor_body,
            )

        date_value = "2021"
        date_fields = form_fields(self.get(edit_url))
        date_fields["date_issued_year"] = date_value
        after_date_body, landed_url = self.post(edit_url, edit_url, date_fields)
        if urllib.parse.urlparse(landed_url).path != item_path:
            self.fail(
                landed_url,
                200,
                f"dating the reference did not redirect to its own page (landed on {landed_url})",
                after_date_body,
            )
        if date_value not in after_date_body:
            self.fail(
                landed_url,
                200,
                f"reference page does not show the date {date_value!r} after saving",
                after_date_body,
            )

        identifier_value = f"10.9999/smoke-{uuid.uuid4().hex[:8]}"
        identifier_fields = form_fields(self.get(edit_url))
        identifier_fields["item_identifiers-0-type"] = "DOI"
        identifier_fields["item_identifiers-0-value"] = identifier_value
        after_identifier_body, landed_url = self.post(
            edit_url, edit_url, identifier_fields
        )
        if urllib.parse.urlparse(landed_url).path != item_path:
            self.fail(
                landed_url,
                200,
                f"adding an identifier did not redirect to the reference's own page (landed on {landed_url})",
                after_identifier_body,
            )
        if identifier_value not in after_identifier_body:
            self.fail(
                landed_url,
                200,
                f"reference page does not show the identifier {identifier_value!r} after saving",
                after_identifier_body,
            )

        delete_match = DELETE_LINK_RE.search(after_identifier_body)
        if delete_match is None:
            self.fail(
                landed_url,
                200,
                "no Delete link on the reference used for the related-row walk",
                after_identifier_body,
            )
        delete_url = f"{self.base_url}{delete_match.group('path')}"
        delete_fields = form_fields(self.get(delete_url))
        self.post(delete_url, delete_url, delete_fields)

    def walk_import(self, list_url, list_body):
        """Preview the fixture file, confirm it, and check the catalogue and its message (FS-011).

        Asserts that the preview lands on its own address, reports the two entries that
        convert and the one that does not with an actionable reason
        (demo/seed/import-sample.bib), and leaves the catalogue unchanged. Confirming
        then redirects to the catalogue with a message stating the counts, and the
        catalogue is re-fetched to confirm the references arrived.

        Args:
            list_url: The catalogue list's address.
            list_body: The catalogue list's HTML.
        """
        import_match = IMPORT_LINK_RE.search(list_body)
        if import_match is None:
            self.fail(list_url, 200, "no Import link on the catalogue list", list_body)
        import_url = f"{self.base_url}{import_match.group('path')}"
        preview_url = f"{import_url}preview/"

        import_form_body = self.get(import_url)
        fields = form_fields(import_form_body)
        if "format" not in fields or "file" not in fields:
            self.fail(
                import_url,
                200,
                "the import form carries no format or file control",
                import_form_body,
            )

        text_fields = {key: value for key, value in fields.items() if key != "file"}
        text_fields["format"] = "bibtex"
        body, content_type = encode_multipart(
            text_fields,
            {
                "file": (
                    IMPORT_FIXTURE_PATH.name,
                    IMPORT_FIXTURE_PATH.read_bytes(),
                    "application/octet-stream",
                )
            },
        )
        headers = {"Referer": import_url, "Content-Type": content_type}
        request = urllib.request.Request(import_url, data=body, headers=headers)  # noqa: S310 — http(s) only, built from base_url argv, never external input
        preview_body, landed_url = self.fetch(request, import_url)

        if landed_url != preview_url:
            self.fail(
                landed_url,
                200,
                f"submitting the import did not redirect to its own preview address (landed on {landed_url})",
                preview_body,
            )
        if "preview" not in preview_body.lower():
            self.fail(
                preview_url,
                200,
                "the preview address was not rendered as a preview",
                preview_body,
            )
        self._check_import_report(preview_url, preview_body, "the preview")

        list_before_confirm = self.get(list_url)
        for created_title in (
            "Field Notes on Alpine Meltwater Monitoring",
            "Notes Toward a Typology of Silence",
        ):
            if created_title in list_before_confirm:
                self.fail(
                    list_url,
                    200,
                    f"the catalogue already lists {created_title!r} before the preview was confirmed",
                    list_before_confirm,
                )

        # Restart discards the staged file; it is exercised here before the real run.
        restart_match = RESTART_IMPORT_RE.search(preview_body)
        if restart_match is None:
            self.fail(
                preview_url, 200, "the preview carries no restart control", preview_body
            )
        restart_url = f"{self.base_url}{restart_match.group('path')}"
        restart_form_body = preview_body[restart_match.start() :]
        form_after_restart_body, landed_url = self.post(
            restart_url, preview_url, form_fields(restart_form_body)
        )
        if landed_url != import_url:
            self.fail(
                landed_url,
                200,
                f"restarting did not redirect to an empty import form (landed on {landed_url})",
                form_after_restart_body,
            )
        restarted_fields = form_fields(form_after_restart_body)
        if restarted_fields.get("file"):
            self.fail(
                import_url,
                200,
                "the form restarting lands on still carries a file value",
                form_after_restart_body,
            )

        # Restart discarded the staged file, so preview it again as a reader would.
        body, content_type = encode_multipart(
            text_fields,
            {
                "file": (
                    IMPORT_FIXTURE_PATH.name,
                    IMPORT_FIXTURE_PATH.read_bytes(),
                    "application/octet-stream",
                )
            },
        )
        headers = {"Referer": import_url, "Content-Type": content_type}
        request = urllib.request.Request(import_url, data=body, headers=headers)  # noqa: S310 — http(s) only, built from base_url argv, never external input
        preview_body, landed_url = self.fetch(request, import_url)
        if landed_url != preview_url:
            self.fail(
                landed_url,
                200,
                f"re-previewing after a restart did not redirect to the preview address (landed on {landed_url})",
                preview_body,
            )

        confirm_match = CONFIRM_IMPORT_RE.search(preview_body)
        if confirm_match is None:
            self.fail(
                preview_url, 200, "the preview carries no confirm control", preview_body
            )
        confirm_url = f"{self.base_url}{confirm_match.group('path')}"

        confirm_form_body = preview_body[confirm_match.start() :]
        list_after_confirm_body, landed_url = self.post(
            confirm_url, preview_url, form_fields(confirm_form_body)
        )
        if landed_url != list_url:
            self.fail(
                landed_url,
                200,
                f"confirming the preview did not redirect to the catalogue (landed on {landed_url})",
                list_after_confirm_body,
            )
        if "2 created" not in list_after_confirm_body:
            self.fail(
                list_url,
                200,
                "the catalogue does not carry a message stating the counts after confirming",
                list_after_confirm_body,
            )

        list_after_import = self.get(list_url)
        for created_title in (
            "Field Notes on Alpine Meltwater Monitoring",
            "Notes Toward a Typology of Silence",
        ):
            if created_title not in list_after_import:
                self.fail(
                    list_url,
                    200,
                    f"the catalogue does not list the imported reference {created_title!r}",
                    list_after_import,
                )

    def _check_import_report(self, url, body, what):
        """Check the three assertions a preview and a real report both satisfy (FS-011).

        Args:
            url: The address the body was fetched from.
            body: The report's HTML.
            what: How to name the page in a failure message.
        """
        for created_key in ("ImportFixtureAlpha2024", "ImportFixtureBeta2023"):
            if created_key not in body:
                self.fail(
                    url,
                    200,
                    f"{what} does not carry the fixture's created entry {created_key!r}",
                    body,
                )
        if "ImportFixtureGamma2022" not in body:
            self.fail(
                url,
                200,
                f"{what} does not carry the fixture's failing entry 'ImportFixtureGamma2022'",
                body,
            )
        if "Ensure this value has at most 255 characters" not in body:
            self.fail(
                url, 200, f"{what} does not carry the failing entry's own reason", body
            )

    def sign_in(self):
        """Sign in as the demo's editor through the admin's login page.

        Uses the opener directly, as ``fetch`` fails any response that lands on a
        login page. Fails if the sign-in is refused and lands back on that page.
        """
        login_url = f"{self.base_url}{SIGN_IN_PATH}?next=/catalogue/"
        try:
            with self.opener.open(login_url, timeout=10) as response:
                fields = form_fields(response.read().decode("utf-8", errors="replace"))
            fields["username"] = EDITOR_USERNAME
            fields["password"] = EDITOR_PASSWORD
            data = urllib.parse.urlencode(fields).encode("ascii")
            request = urllib.request.Request(  # noqa: S310 — http(s) only, built from base_url argv
                login_url, data=data, headers={"Referer": login_url}
            )
            with self.opener.open(request, timeout=10) as response:
                body = response.read().decode("utf-8", errors="replace")
                final_url = response.geturl()
        except urllib.error.HTTPError as exc:
            self.fail(login_url, exc.code, "unsuccessful response", exc.read().decode())
        except urllib.error.URLError as exc:
            self.fail(login_url, None, f"could not connect: {exc.reason}")

        if "login" in urllib.parse.urlparse(final_url).path.lower():
            self.fail(login_url, 200, f"{EDITOR_USERNAME} could not sign in", body)

    def get(self, url):
        """GET a URL, following redirects, and fail if any lands on a login page (FS-007).

        Args:
            url: The address to fetch.

        Returns:
            The response body.
        """
        body, _final_url = self.fetch(url, url)
        return body

    def post(self, url, referer, fields):
        """POST fields to a URL through the walk's shared opener (FS-008).

        Args:
            url: The address to post to.
            referer: The page the form was rendered on, sent as a browser would.
            fields: The form fields, name to value.

        Returns:
            The body and the final URL, so a caller can assert where the response
            landed as well as what it carries.
        """
        data = urllib.parse.urlencode(fields).encode("ascii")
        request = urllib.request.Request(url, data=data, headers={"Referer": referer})  # noqa: S310 — http(s) only, built from base_url argv, never external input
        return self.fetch(request, url)

    def fetch(self, request, display_url):
        """Send a request through the shared opener, failing on an error or a login page (FS-007).

        Args:
            request: A URL string or a ``urllib.request.Request``.
            display_url: The address a failure reports.

        Returns:
            The body and the final URL.
        """
        try:
            with self.opener.open(request, timeout=10) as response:
                body = response.read().decode("utf-8", errors="replace")
                final_url = response.geturl()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            self.fail(display_url, exc.code, "unsuccessful response", body)
        except urllib.error.URLError as exc:
            self.fail(display_url, None, f"could not connect: {exc.reason}")

        # Every page the walk reaches is open to it, so a login redirect is a failure (FS-007).
        if "login" in urllib.parse.urlparse(final_url).path.lower():
            self.fail(
                display_url,
                200,
                f"redirected to a login page ({final_url})",
                body,
            )

        return body, final_url

    def fail(self, url, status, reason, body=""):
        """Raise ``SmokeCheckFailed`` with a bounded excerpt of body.

        Args:
            url: The address that failed.
            status: The HTTP status, or ``None`` if there was none.
            reason: What the check found wrong.
            body: The response body, cut to ``BODY_EXCERPT_LIMIT``.

        Raises:
            SmokeCheckFailed: Always.
        """
        excerpt = body[:BODY_EXCERPT_LIMIT]
        raise SmokeCheckFailed(f"{url} [{status}]: {reason}\n{excerpt}")


def main(argv):
    """Run the walk against ``argv[1]`` as the base URL, or ``http://127.0.0.1:8000`` if absent.

    Args:
        argv: The command-line arguments.

    Returns:
        The process exit code: 0 on success, 1 if a check failed.
    """
    base_url = argv[1] if len(argv) > 1 else "http://127.0.0.1:8000"
    try:
        DemoWalk(base_url).run()
    except SmokeCheckFailed as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    print(
        f"OK: walked the demo catalogue, its second page, a reference and a contributor, "
        f"created/corrected/removed a reference, credited a contributor, dated a reference, "
        f"identified a reference, and imported a bibliography file, at {base_url}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
