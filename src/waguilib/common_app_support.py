import inspect
from pathlib import Path

from waguilib.importable_settings import INTERNAL_APP_ROOT


class WaRuntimeSupport:

    #: The actual basename of local configuration file, to be overridden
    _config_file_basename = None

    def _get_class_package_path(self):
        """Guess the Path of the folder where this (sub)class is defined"""
        return Path(inspect.getfile(self.__class__)).parent

    @property
    def config_schema_path(self) -> Path:
        """Return the schema to validate config files. """
        return self._get_class_package_path().joinpath("config_schema.json")

    @property
    def config_template_path(self) -> Path:
        """Return the model for config file initialization."""
        return self._get_class_package_path().joinpath("config_template.ini")

    @property
    def config_file_path(self) -> Path:
        """"Return the actual, runtime configuration file."""
        return INTERNAL_APP_ROOT / self._config_file_basename  # Might no exist yet

