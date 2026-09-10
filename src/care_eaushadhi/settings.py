from typing import Any

import environ
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.signals import setting_changed
from django.dispatch import receiver
from rest_framework.settings import perform_import

from care_eaushadhi.apps import PLUGIN_NAME

env = environ.Env()


class LazyConfigValue:
    """Generic lazy evaluation wrapper for configuration values.

    Validates only when the value is actually used, not at import time.
    This allows CARE Docker images to build without all settings configured.
    """

    def __init__(self, setting_name: str, error_message: str):
        self.setting_name = setting_name
        self.error_message = error_message
        self._validated = False
        self._value = None

    def _validate(self):
        """Validate and cache the setting value on first access."""
        if not self._validated:
            # Import here to avoid circular dependency
            value = getattr(plugin_settings, self.setting_name)
            if not value:
                raise ImproperlyConfigured(self.error_message)
            self._value = value
            self._validated = True
        return self._value

    def __str__(self):
        return str(self._validate())

    def __repr__(self):
        return f"LazyConfigValue({self.setting_name})"

    def __eq__(self, other):
        return str(self) == other

    def __hash__(self):
        return hash(str(self))

    def __add__(self, other):
        return str(self) + other

    def __radd__(self, other):
        return other + str(self)

    def __bool__(self):
        try:
            return bool(self._validate())
        except ImproperlyConfigured:
            return False


class PluginSettings:  # pragma: no cover
    """
    A settings object that allows plugin settings to be accessed as
    properties. For example:

        from plugin.settings import plugin_settings
        print(plugin_settings.API_KEY)

    Any setting with string import paths will be automatically resolved
    and return the class, rather than the string literal.

    """

    def __init__(
        self,
        plugin_name: str = None,
        defaults: dict | None = None,
        import_strings: set | None = None,
        required_settings: set | None = None,
    ) -> None:
        if not plugin_name:
            raise ValueError("Plugin name must be provided")
        self.plugin_name = plugin_name
        self.defaults = defaults or {}
        self.import_strings = import_strings or set()
        self.required_settings = required_settings or set()
        self._cached_attrs = set()
        self.validate()

    def __getattr__(self, attr) -> Any:
        if attr not in self.defaults:
            raise AttributeError("Invalid setting: '%s'" % attr)

        # Try to find the setting from user settings, then from environment variables
        val = self.defaults[attr]
        try:
            val = self.user_settings[attr]
        except KeyError:
            try:
                val = env(attr, cast=type(val))
            except environ.ImproperlyConfigured:
                # Fall back to defaults
                pass

        # Coerce import strings into classes
        if attr in self.import_strings:
            val = perform_import(val, attr)

        self._cached_attrs.add(attr)
        setattr(self, attr, val)
        return val

    @property
    def user_settings(self) -> dict:
        if not hasattr(self, "_user_settings"):
            self._user_settings = getattr(settings, "PLUGIN_CONFIGS", {}).get(
                self.plugin_name, {}
            )
        return self._user_settings

    def validate(self) -> None:
        """
        This method handles the validation of the plugin settings.
        It could be overridden to provide custom validation logic.

        the base implementation checks if all the required settings are truthy.
        """
        for setting in self.required_settings:
            try:
                value = getattr(self, setting)
                if value is None or (isinstance(value, str) and value == ""):
                    raise ImproperlyConfigured(
                        f'The "{setting}" setting is required. '
                        f'Please set the "{setting}" in the environment or the {PLUGIN_NAME} plugin config.'
                    )
            except AttributeError as exc:
                raise ImproperlyConfigured(
                    f'The "{setting}" setting is required. '
                    f'Please set the "{setting}" in the environment or the {PLUGIN_NAME} plugin config.'
                ) from exc
            
    def reload(self) -> None:
        """
        Deletes the cached attributes so they will be recomputed next time they are accessed.
        """
        for attr in self._cached_attrs:
            delattr(self, attr)
        self._cached_attrs.clear()
        if hasattr(self, "_user_settings"):
            delattr(self, "_user_settings")


# Settings are now lazily validated when accessed, not at import time
# This allows Docker builds without complete configuration
REQUIRED_SETTINGS = set()

DEFAULTS = {
    "EAUSHADHI_API_ENDPOINT": "",
    "EAUSHADHI_API_SECRET_KEY": "",
    "EAUSHADHI_DEPLOYMENT": "karnataka",
    "EAUSHADHI_API_RETRY_COUNT": 5,
    "EAUSHADHI_API_TIMEOUT": 30,
    "EAUSHADHI_API_CONNECT_TIMEOUT": 10,
    "EAUSHADHI_API_READ_TIMEOUT": 30,
    "EAUSHADHI_API_VERIFY_SSL": True,
    "EAUSHADHI_API_PROXY_HTTP": "",
    "EAUSHADHI_API_PROXY_HTTPS": "",
    "EAUSHADHI_SIMILARITY_THRESHOLD": 0.3,
    "EAUSHADHI_STRICT_QUANTITY_VALIDATION": True,
    "EAUSHADHI_VALIDATION_ENABLED": True,
}

plugin_settings = PluginSettings(
    PLUGIN_NAME, defaults=DEFAULTS, required_settings=REQUIRED_SETTINGS
)


# Lazy configuration values - validated only when accessed, not at import time
EAUSHADHI_API_ENDPOINT = LazyConfigValue(
    "EAUSHADHI_API_ENDPOINT",
    "EAUSHADHI_API_ENDPOINT is required for eAushadhi integration. "
    "Please configure it in PLUGIN_CONFIGS or environment variables."
)

EAUSHADHI_API_SECRET_KEY = LazyConfigValue(
    "EAUSHADHI_API_SECRET_KEY",
    "EAUSHADHI_API_SECRET_KEY is required for eAushadhi API authentication. "
    "Please configure it in PLUGIN_CONFIGS or environment variables."
)


@receiver(setting_changed)
def reload_plugin_settings(*args, **kwargs) -> None:
    setting = kwargs["setting"]
    if setting == "PLUGIN_CONFIGS":
        plugin_settings.reload()
