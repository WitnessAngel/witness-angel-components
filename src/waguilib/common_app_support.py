import inspect
from pathlib import Path

from kivy.properties import StringProperty

from waguilib.importable_settings import INTERNAL_APP_ROOT, INTERNAL_CONTAINERS_DIR, INTERNAL_KEYS_DIR, \
    INTERNAL_LOGS_DIR
from waguilib.i18n import tr


class WaRuntimeSupportMixin:

    # Big status text to be displayed wherever possible
    checkup_status_text = None

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
    def config_template_path(self) -> Path:  # FIXME rename to DEFAULTS!!
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

    def _get_status_checkers(self) -> list:
        """Return ready-to-call bound checkers from below"""
        raise NotImplementedError("_get_status_checkers")

    def refresh_checkup_status(self) -> bool:
        status_checkers = self._get_status_checkers()

        global_status = True
        checkup_status_messages = []

        for status_checker in status_checkers:
            status, message = status_checker()
            global_status = global_status and status
            checkup_status_messages.append(("[OK]" if status else "[KO]") + " " + message)

        self.checkup_status_text = "\n".join(checkup_status_messages)
        return global_status

    @staticmethod
    def check_container_output_dir(container_dir: Path):
        if container_dir and container_dir.is_dir():
            return True, tr.f(tr._("Container storage: {container_dir}"))

        return False, tr.f(tr._("Invalid container storage: \"{container_dir}\""))

    @staticmethod
    def check_keyguardian_counts(keyguardian_threshold, keyguardian_count):
        if 0 < keyguardian_threshold <= keyguardian_count:
            return True, tr.f(tr._("{keyguardian_count} key guardian(s) configured, {keyguardian_threshold} of which necessary for decryption"))
        return False, tr.f(tr._("{keyguardian_count} key guardian(s) configured, while {keyguardian_threshold} of which necessary for decryption"))

    @staticmethod
    def check_camera_url(camera_url):
        from urllib.parse import urlparse
        if camera_url:
            try:
                parsed = urlparse(camera_url)
                if parsed.scheme:
                    return True, tr.f(tr._("Camera url: {camera_url}"))
            except ValueError:
                pass
        return False, tr.f(tr._("Wrong camera url: \"{camera_url}\""))
