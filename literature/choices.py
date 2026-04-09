"""CSL JSON choices enumerations for the literature app.

Provides TextChoices enums for:
- ItemType: all 45 CSL JSON 1.0.2 item type values
- NameRole: all 26 CSL name-variable role fields
- DateType: all 6 CSL date-variable slot names
- IdentifierType: 6 known CSL identifier field names

References:
- https://resource.citationstyles.org/schema/v1.0/input/json/csl-data.json
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class ItemType(models.TextChoices):
    """CSL JSON 1.0.2 item type enumeration (45 values).

    Four types use underscores in the CSL JSON 1.0.2 schema
    (legal_case, motion_picture, musical_score, personal_communication)
    and are stored with underscores. All other types use hyphens.

    Reference: https://resource.citationstyles.org/schema/v1.0/input/json/csl-data.json
    """

    ARTICLE = "article", _("Article")
    ARTICLE_JOURNAL = "article-journal", _("Journal Article")
    ARTICLE_MAGAZINE = "article-magazine", _("Magazine Article")
    ARTICLE_NEWSPAPER = "article-newspaper", _("Newspaper Article")
    BILL = "bill", _("Bill")
    BOOK = "book", _("Book")
    BROADCAST = "broadcast", _("Broadcast")
    CHAPTER = "chapter", _("Chapter")
    CLASSIC = "classic", _("Classic")
    COLLECTION = "collection", _("Collection")
    DATASET = "dataset", _("Dataset")
    DOCUMENT = "document", _("Document")
    ENTRY = "entry", _("Entry")
    ENTRY_DICTIONARY = "entry-dictionary", _("Dictionary Entry")
    ENTRY_ENCYCLOPEDIA = "entry-encyclopedia", _("Encyclopedia Entry")
    EVENT = "event", _("Event")
    FIGURE = "figure", _("Figure")
    GRAPHIC = "graphic", _("Graphic")
    HEARING = "hearing", _("Hearing")
    INTERVIEW = "interview", _("Interview")
    LEGAL_CASE = "legal_case", _("Legal Case")
    LEGISLATION = "legislation", _("Legislation")
    MANUSCRIPT = "manuscript", _("Manuscript")
    MAP = "map", _("Map")
    MOTION_PICTURE = "motion_picture", _("Motion Picture")
    MUSICAL_SCORE = "musical_score", _("Musical Score")
    PAMPHLET = "pamphlet", _("Pamphlet")
    PAPER_CONFERENCE = "paper-conference", _("Conference Paper")
    PATENT = "patent", _("Patent")
    PERFORMANCE = "performance", _("Performance")
    PERIODICAL = "periodical", _("Periodical")
    PERSONAL_COMMUNICATION = "personal_communication", _("Personal Communication")
    POST = "post", _("Post")
    POST_WEBLOG = "post-weblog", _("Blog Post")
    REGULATION = "regulation", _("Regulation")
    REPORT = "report", _("Report")
    REVIEW = "review", _("Review")
    REVIEW_BOOK = "review-book", _("Book Review")
    SOFTWARE = "software", _("Software")
    SONG = "song", _("Song")
    SPEECH = "speech", _("Speech")
    STANDARD = "standard", _("Standard")
    THESIS = "thesis", _("Thesis")
    TREATY = "treaty", _("Treaty")
    WEBPAGE = "webpage", _("Webpage")


class NameRole(models.TextChoices):
    """CSL JSON name-variable role enumeration (26 values).

    Covers all 26 CSL name-variable fields that identify contributors
    to a bibliographic item and their role.

    Reference: CSL JSON 1.0.2 schema name-variable fields.
    """

    AUTHOR = "author", _("Author")
    CHAIR = "chair", _("Chair")
    COLLECTION_EDITOR = "collection-editor", _("Collection Editor")
    COMPILER = "compiler", _("Compiler")
    COMPOSER = "composer", _("Composer")
    CONTAINER_AUTHOR = "container-author", _("Container Author")
    CONTRIBUTOR = "contributor", _("Contributor")
    CURATOR = "curator", _("Curator")
    DIRECTOR = "director", _("Director")
    EDITOR = "editor", _("Editor")
    EDITORIAL_DIRECTOR = "editorial-director", _("Editorial Director")
    EXECUTIVE_PRODUCER = "executive-producer", _("Executive Producer")
    GUEST = "guest", _("Guest")
    HOST = "host", _("Host")
    ILLUSTRATOR = "illustrator", _("Illustrator")
    INTERVIEWER = "interviewer", _("Interviewer")
    NARRATOR = "narrator", _("Narrator")
    ORGANIZER = "organizer", _("Organizer")
    ORIGINAL_AUTHOR = "original-author", _("Original Author")
    PERFORMER = "performer", _("Performer")
    PRODUCER = "producer", _("Producer")
    RECIPIENT = "recipient", _("Recipient")
    REVIEWED_AUTHOR = "reviewed-author", _("Reviewed Author")
    SCRIPT_WRITER = "script-writer", _("Script Writer")
    SERIES_CREATOR = "series-creator", _("Series Creator")
    TRANSLATOR = "translator", _("Translator")


class DateType(models.TextChoices):
    """CSL JSON date-variable slot enumeration (6 values).

    Maps to the CSL JSON date-variable field names that can appear
    on a bibliographic item object.

    Reference: CSL JSON 1.0.2 schema date-variable fields.
    """

    ACCESSED = "accessed", _("Accessed")
    AVAILABLE_DATE = "available-date", _("Available Date")
    EVENT_DATE = "event-date", _("Event Date")
    ISSUED = "issued", _("Issued")
    ORIGINAL_DATE = "original-date", _("Original Date")
    SUBMITTED = "submitted", _("Submitted")


class IdentifierType(models.TextChoices):
    """Known CSL JSON identifier field enumeration (6 values).

    Lists the well-known identifier field names extracted as top-level
    CSL JSON properties. Unknown identifier types are also stored but
    without choices validation (FR-017).

    Pure acronym labels (DOI, ISBN, ISSN, PMID, PMCID, URL) are exempt
    from i18n wrapping per FR-018.
    """

    DOI = "DOI", "DOI"
    ISBN = "ISBN", "ISBN"
    ISSN = "ISSN", "ISSN"
    PMID = "PMID", "PMID"
    PMCID = "PMCID", "PMCID"
    URL = "URL", "URL"
