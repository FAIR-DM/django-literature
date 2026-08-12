from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LiteratureUIConfig(AppConfig):
    """Django AppConfig for the opt-in catalogue front end."""

    name = "literature.ui"
    label = "literature_ui"
    verbose_name = _("Literature UI")
