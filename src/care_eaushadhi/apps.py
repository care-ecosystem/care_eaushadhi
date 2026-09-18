import sys

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

PLUGIN_NAME = "care_eaushadhi"

BUILD_TIME_COMMANDS = {
    "collectstatic",
    "makemigrations",
    "migrate",
    "compilemessages",
    "makemessages",
    "spectacular",
    "test",
}


class Care_eaushadhiConfig(AppConfig):
    name = PLUGIN_NAME
    verbose_name = _("Care_eaushadhi")

    def ready(self):
        import care_eaushadhi.signals       # noqa F401
        import care_eaushadhi.tasks         # noqa F401

        # Register permission so it syncs to DB and appears in UI
        from care.security.permissions.base import PermissionController
        from care_eaushadhi.security.EAushadhiPermissions import EAushadhiPermissions

        PermissionController.register_permission_handler(EAushadhiPermissions)

        # Register authorization handler
        import care_eaushadhi.security.EAushadhiAccess  # noqa F401

        # Validate required settings at runtime only. Build-time commands
        if len(sys.argv) > 1 and sys.argv[1] in BUILD_TIME_COMMANDS:
            return

        from care_eaushadhi.settings import plugin_settings

        plugin_settings.validate()
