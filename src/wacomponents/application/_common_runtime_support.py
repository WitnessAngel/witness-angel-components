import inspect
from pathlib import Path

from wacomponents.default_settings import INTERNAL_APP_ROOT, INTERNAL_CRYPTAINER_DIR, INTERNAL_KEYSTORE_POOL_DIR, \
    INTERNAL_LOGS_DIR
from wacomponents.i18n import tr


class WaRuntimeSupportMixin:
    """
    Runtime utilities for both GUI and non-GUI applications!
    """
    # Big status text to be displayed wherever possible
    checkup_status_text = None

    #: The actual basename of local configuration file, to be overridden
    _config_file_basename = None

    def _get_class_package_path(self):
        """Guess the Path of the folder where the object's real (sub)class is defined"""
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
        return str(INTERNAL_KEYSTORE_POOL_DIR)

    @property
    def internal_cryptainer_dir(self) -> str:  # FIXME switch to Path!
        """For all local containers"""
        return str(INTERNAL_CRYPTAINER_DIR)

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

    ## SETTING CHECKERS - might have to access instance properties someday... ##

    @staticmethod
    def check_cryptainer_output_dir(cryptainer_dir: Path):
        if cryptainer_dir and cryptainer_dir.is_dir():
            return True, tr.f(tr._("Container storage: {cryptainer_dir}"))

        return False, tr.f(tr._("Invalid container storage: \"{cryptainer_dir}\""))

    @staticmethod
    def check_keyguardian_counts(keyguardian_threshold, keyguardian_count):
        message = tr.f(tr._("{keyguardian_count} key guardian(s) configured, {keyguardian_threshold} of which necessary for decryption"))
        if 0 < keyguardian_threshold <= keyguardian_count:
            return True, message
        return False, message

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

    @staticmethod
    def check_video_recording_duration_mn(video_recording_duration_mn):
        message = tr.f(tr._("Each container stores {video_recording_duration_mn} mn(s) of video"))
        if video_recording_duration_mn > 0:
            return True, message
        return False, message

    @staticmethod
    def check_max_cryptainer_age_day(max_cryptainer_age_day):
        message = tr.f(tr._("Containers are kept for {max_cryptainer_age_day} day(s)"))
        if max_cryptainer_age_day > 0:
            return True, message
        return False, message

