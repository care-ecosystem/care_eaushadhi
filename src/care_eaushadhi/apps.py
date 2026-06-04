from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

PLUGIN_NAME = "care_eaushadhi"


class Care_eaushadhiConfig(AppConfig):
    name = PLUGIN_NAME
    verbose_name = _("Care_eaushadhi")

    def ready(self):
        import care_eaushadhi.signals  # noqa F401
        # Import tasks to register Celery tasks
        import care_eaushadhi.tasks  # noqa: F401

