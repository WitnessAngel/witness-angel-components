import inspect
from pathlib import Path

from waguilib.importable_settings import INTERNAL_APP_ROOT, INTERNAL_CONTAINERS_DIR, INTERNAL_KEYS_DIR, \
    INTERNAL_LOGS_DIR


class WaRuntimeSupportMixin:

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

    @property
    def internal_keys_dir(self) -> str:  # FIXME switch to Path!
        """For the pool of imported and local keys"""
        return str(INTERNAL_KEYS_DIR)

    @property
    def internal_containers_dir(self) -> str:  # FIXME switch to Path!
        """For all local containers"""
        return str(INTERNAL_CONTAINERS_DIR)

    @property
    def internal_logs_dir(self) -> str:  # FIXME switch to Path!
        """For all app logs"""
        return str(INTERNAL_LOGS_DIR)
