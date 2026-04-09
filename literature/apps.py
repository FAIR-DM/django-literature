from django.apps import AppConfig


class LiteratureConfig(AppConfig):
    """Django AppConfig for the literature app."""

    name = "literature"
    label = "literature"
    default_auto_field = "django.db.models.BigAutoField"
    verbose_name = "Literature"
