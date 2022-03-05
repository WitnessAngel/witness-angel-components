import json

import functools
from kivy.clock import Clock
from kivy.uix.settings import SettingsWithSpinner
from kivymd.app import MDApp

from wacomponents.application._common_runtime_support import WaRuntimeSupportMixin
from wacomponents.widgets.layout_components import SettingStringTruncated


class ImprovedSettingsWithSpinner(SettingsWithSpinner):
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self.register_type('string_truncated', SettingStringTruncated)


class WaGenericGui(WaRuntimeSupportMixin, MDApp):
    """
    Base class for standalone KIVY GUI applications, which don't need a client/service functioning.
    """

    # CLASS VARIABLES TO BE OVERRIDEN #
    title_app_window: str = None
    title_conf_panel: str = None

    use_kivy_settings = False  # No need

    settings_cls = ImprovedSettingsWithSpinner

    def build(self):
        self.title = self.title_app_window  # We properly use this Kivy property
        self.theme_cls.primary_palette = "Blue"
        #self.theme_cls.theme_style = "Dark"  # or "Light"
        self.theme_cls.primary_hue = "900"  # "500"

    def on_pause(self):
        """Enables the user to switch to another application, causing the app to wait
        until the user switches back to it eventually.
        """
        return True

    def on_resume(self):
        """Called when the app is resumed. Used to restore data that has been
        stored in on_pause().
        """
        pass

    # SETTINGS BUILDING AND SAVING #

    def load_config(self):
        # Hook here if needed
        ##Path(self.get_application_config()).touch(exist_ok=True)  # For initial creation
        config = super().load_config()
        return config  # Might have unsaved new DEFAULTS in it, which will be saved on any setting update

    def build_config(self, config):
        """Populate config with default values, before the loading of user preferences."""
        assert self.config_defaults_path.exists(), self.config_defaults_path
        #print(">>>>>>>>>>>>>>READING config_template_path"),
        config.read(str(self.config_defaults_path))
        '''
        config.filename = self.get_application_config()
        if not os.path.exists(config.filename):
            config.write()  # Initial user preferences file
            '''

    def build_settings(self, settings):
        """Read the settings schema and create a panel from it."""
        data = json.dumps(self.get_config_schema_data())
        settings.add_json_panel(
            title=self.title_conf_panel, config=self.config, data=data
        )

    def close_settings(self, *args, **kwargs):
        # Hook in case of need
        super().close_settings(*args, **kwargs)

    def save_config(self):
        """Dump current config to local INI file."""
        assert self.config.filename, self.config.filename
        #print(">>>>>>>>>>>>>>WRITING save_config", self.config_file_path),
        self.config.filename = self.config_file_path
        self.config.write()

    def get_application_config(self, *args, **kwargs):
        # IMPORTANT override of Kivy method #
        #print(">>>>>>>>>>>>>>READING get_application_config"),
        return str(self.config_file_path)

    # MISC UTILITIES #

    def _schedule_once(self, callable, *args, **kwargs):
        """Schedule a task for single launch on main GUI thread."""
        callback = functools.partial(callable, *args, **kwargs)
        Clock.schedule_once(callback)
