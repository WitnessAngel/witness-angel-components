# -*- coding: utf-8 -*-
import atexit
from pathlib import Path

import functools
import logging
import os

from waguilib.common_app_support import WaRuntimeSupportMixin

os.environ["KIVY_NO_ARGS"] = "1"

import kivy
kivy.require("2.0.0")

from kivymd.app import MDApp
from kivy.clock import Clock
from kivy.logger import Logger as logger
from kivy.uix.filechooser import filesize_units
from kivy.uix.settings import SettingsWithTabbedPanel

from oscpy.server import ServerClass
from waguilib.service_control import ServiceController
from waguilib.logging.handlers import CallbackHandler, safe_catch_unhandled_exception
from waguilib.service_control.osc_transport import get_osc_server



osc, osc_starter_callback = get_osc_server(is_master=True)


@ServerClass
class WAGuiApp(WaRuntimeSupportMixin, MDApp):  # FIXME WaGui instead?
    """
    Main GUI app, which controls the recording service (via OSC protocol), and
    exposes settings as well as existing containers.
    """

    # CLASS VARIABLES TO BE OVERRIDEN #
    title: str = None
    #app_config_file: str = None
    #default_config_template: str = None
    #default_config_schema: str = None
    wip_recording_marker: str = None

    service_querying_interval = 1  # To check when service is ready, at app start
    use_kivy_settings = False  # No need

    language = None  # TO OVERRIDE at instance level

    settings_cls = SettingsWithTabbedPanel

    def __init__(self, **kwargs):
        self._unanswered_service_state_requests = 0  # Used to detect a service not responding anymore to status requests
        print("STARTING INIT OF WitnessAngelClientApp")
        super(WAGuiApp, self).__init__(**kwargs)
        print("AFTER PARENT INIT OF WitnessAngelClientApp")
        osc_starter_callback()  # Opens server port
        print("FINISHED INIT OF WitnessAngelClientApp")

    # SETTINGS BUILDING AND SAVING #

    def load_config(self):
        # Hook here if needed
        ##Path(self.get_application_config()).touch(exist_ok=True)  # For initial creation
        config = super().load_config()
        return config

    def build_config(self, config):
        """Populate config with default values, before the loading of user preferences."""
        assert self.config_template_path.exists(), self.config_template_path
        #print(">>>>>>>>>>>>>>READING config_template_path"),
        config.read(str(self.config_template_path))
        '''
        config.filename = self.get_application_config()
        if not os.path.exists(config.filename):
            config.write()  # Initial user preferences file
            '''

    def build_settings(self, settings):
        """Read the user settings schema and create a panel from it."""
        settings_file = self.default_config_schema
        settings.add_json_panel(
            title=self.title, config=self.config, filename=settings_file
        )

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

    # APP LIFECYCLE AND RECORDING STATE #

    def set_recording_btn_state(self, pushed: bool=None, disabled: bool=None):
        assert pushed is not None or disabled is not None, (pushed, disabled)
        recording_btn = self.recording_button  # Must have been defined on subclass!
        if pushed is not None:
            recording_btn.state = "down" if pushed else "normal"
        if disabled is not None:
            recording_btn.disabled = disabled

    def on_pause(self):
        """Enables the user to switch to another application, causing the app to wait
        until the user switches back to it eventually.
        """
        print(">>>>>>>>>>>>>>>>>>>>>>>>>>> ON PAUSE HOOK WAS CALLED")
        return True  # ACCEPT pausing

    def on_resume(self):
        """Called when the app is resumed. Used to restore data that has been
        stored in on_pause().
        """
        print(">>>>>>>>>>>>>>>>>>>>>>>>>>> ON RESUME HOOK WAS CALLED")
        pass

    def on_start(self):
        """Event handler for the `on_start` event which is fired after
        initialization (after build() has been called) but before the
        application has started running the events loop.
        """
        self.service_controller = ServiceController()

        # Redirect root logger traffic to GUI console
        logging.getLogger(None).addHandler(CallbackHandler(self.log_output))

        # Constantly check the state of background service
        Clock.schedule_interval(
            self._request_recording_state, self.service_querying_interval
        )
        self._request_recording_state()  # Immediate first iteration

        self.set_recording_btn_state(disabled=True)

        atexit.register(self.on_stop)  # Cleanup in case of crash

    def on_stop(self):
        """Event handler for the `on_stop` event which is fired when the
        application has finished running (i.e. the window is about to be
        closed).
        """
        atexit.unregister(self.on_stop)  # Not needed anymore
        if not self.get_daemonize_service():
            self.service_controller.stop_service()  # Will wait for termination, then kill it

    def _check_recording_configuration(self):
        raise NotImplementedError("_check_recording_configuration")

    def switch_to_recording_state(self, is_recording):
        """
        Might be called as a reaction to the service broadcasting a changed state.
         Let it propagate anyway in this case, the service will just ignore the duplicated command.
        """
        self.set_recording_btn_state(disabled=True)
        wip_recording_marker = Path(self.wip_recording_marker)
        if is_recording:

            if not self._check_recording_configuration():
                # Will automatically notify user if problems, for now
                return

            wip_recording_marker.touch(exist_ok=True)
            self.service_controller.start_recording()
        else:
            try:
                wip_recording_marker.unlink()
            except FileNotFoundError:
                pass
            self.service_controller.stop_recording()

    def _request_recording_state(self, *args, **kwargs):
        """Ask the service for an update on its recording state."""
        self._unanswered_service_state_requests += 1
        if self._unanswered_service_state_requests > 2:
            self._unanswered_service_state_requests = -10  # Leave some time for the service to go online
            logger.info("Launching recorder service")
            self.service_controller.start_service()
        else:
            self.service_controller.broadcast_recording_state()

    @osc.address_method("/receive_recording_state")
    @safe_catch_unhandled_exception
    def receive_recording_state(self, is_recording):
        #print(">>>>> app receive_recording_state", repr(is_recording))
        self._unanswered_service_state_requests = 0  # RESET
        if is_recording == "":  # Special case (ternary value, but None is not supported by OSC)
            self.set_recording_btn_state(disabled=True)
        else:
            self.set_recording_btn_state(pushed=is_recording, disabled=False)

    # SERVICE FEEDBACKS AND DAEMONIZATION #

    def get_daemonize_service(self):  # OVERRIDE THIS TO FETCH USER SETTINGS
        return False

    def switch_daemonize_service(self, value):
        self.service_controller.switch_daemonize_service(value)

    @osc.address_method("/log_output")
    @safe_catch_unhandled_exception
    def _post_log_output(self, msg):
        callback = functools.partial(self.log_output, msg)
        Clock.schedule_once(callback)

    def log_output(self, msg, *args, **kwargs):  # OVERRIDE THIS TO DISPLAY OUTPUT
        pass  # Do nothing by default

    # MISC UTILITIES #

    @staticmethod
    def get_nice_size(size):
        for unit in filesize_units:
            if size < 1024.0:
                return "%1.0f %s" % (size, unit)
            size /= 1024.0
        return size
