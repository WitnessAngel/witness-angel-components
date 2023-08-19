# -*- coding: utf-8 -*-
import logging

import atexit
from kivy.clock import Clock
from kivy.properties import StringProperty
from oscpy.server import ServerClass

from wacomponents.application.generic_gui import WaGenericGui
from wacomponents.default_settings import WAIT_TIME_MULTIPLIER
from wacomponents.i18n import tr
from wacomponents.logging.handlers import safe_catch_unhandled_exception
from wacomponents.service_control import ServiceController
from wacomponents.service_control import get_osc_server
from wacomponents.widgets.popups import display_info_snackbar, display_info_toast

osc, osc_starter_callback = get_osc_server(is_application=True)

logger = logging.getLogger(__name__)


@ServerClass
class WaRecorderGui(WaGenericGui):  # FIXME WaGui instead?
    """
    Main GUI app, which controls the recording service (via OSC protocol), and
    exposes settings as well as existing containers.
    """

    service_querying_interval = 2 * WAIT_TIME_MULTIPLIER  # To check when service is ready, at app start

    # Overridden as property to allow event dispatching in GUI
    assert hasattr(WaGenericGui, "checkup_status_text")
    checkup_status_text = StringProperty("")

    service_controller = None  # To be instantated in start()

    def __init__(self, **kwargs):
        self._unanswered_service_state_requests = (
            0
        )  # Used to detect a service not responding anymore to status requests
        # print("STARTING INIT OF WitnessAngelClientApp")
        super().__init__(**kwargs)
        # print("AFTER PARENT INIT OF WitnessAngelClientApp")
        osc_starter_callback()  # Opens server port
        # print("FINISHED INIT OF WitnessAngelClientApp")

    def close_settings(self, *args, **kwargs):
        super().close_settings(*args, **kwargs)
        display_info_toast(tr._("Some configuration changes might only apply at next recording restart"))

    # APP LIFECYCLE AND RECORDING STATE #

    def _update_app_after_config_change(self):
        """Do not forget to call this super method from child classes"""
        self.refresh_checkup_status()

    def set_recording_btn_state(self, pushed: bool = None, disabled: bool = None):
        assert pushed is not None or disabled is not None, (pushed, disabled)
        recording_btn = self.recording_button  # Must have been defined on subclass!
        if pushed is not None:
            recording_btn.state = "down" if pushed else "normal"
        if disabled is not None:
            recording_btn.disabled = disabled

    def on_start(self):
        """Event handler for the `on_start` event which is fired after
        initialization (after build() has been called) but before the
        application has started running the events loop.
        """
        self.service_controller = ServiceController()

        # Redirect root logger traffic to GUI console widget if wanted
        # logging.getLogger(None).addHandler(CallbackLoggingHandler(self.log_output))

        # Constantly check the state of background service
        Clock.schedule_interval(self._request_recording_state, self.service_querying_interval)
        self._request_recording_state()  # Immediate first iteration

        self.refresh_checkup_status()

        self.set_recording_btn_state(disabled=True)

        atexit.register(self.on_stop)  # Cleanup in case of crash

    def on_stop(self):
        """Event handler for the `on_stop` event which is fired when the
        application has finished running (i.e. the window is about to be
        closed).
        """
        atexit.unregister(self.on_stop)  # Not needed anymore
        if not self.should_daemonize_service():
            self.service_controller.stop_service()  # Will wait for termination, then kill it

    def force_stop_service(self):
        logger.info("GUI forcing shutdown of service")
        self.service_controller.stop_service()  # Does wait for subprocess death
        self.set_recording_btn_state(disabled=True)

    def switch_to_recording_state(self, is_recording):
        """
        Might also be called as a reaction to the service broadcasting a changed state.
         Let it propagate anyway in this case, the service will just ignore the duplicated command.
        """
        logger.debug("GUI calling switch_to_recording_state %r", is_recording)
        self.set_recording_btn_state(disabled=True)
        if is_recording:

            if not self.refresh_checkup_status()[0]:
                display_info_snackbar(tr._("Configuration errors prevent recording"))
                return

            self.service_controller.start_recording()
        else:
            self.service_controller.stop_recording()

    def _request_recording_state(self, *args, **kwargs):
        """Ask the service for an update on its recording state."""
        logger.debug("GUI requesting recording state")
        self._unanswered_service_state_requests += 1
        if self._unanswered_service_state_requests > 2:
            logger.info(
                "Launching recorder service from main app (unanswered requests = %s)",
                self._unanswered_service_state_requests,
            )
            self._unanswered_service_state_requests = -8  # Leave some time for the service to go online
            self.service_controller.start_service()
        else:
            self.service_controller.broadcast_recording_state()

    def _receive_recording_state(self, is_recording, *args, **kwargs):
        logger.debug("GUI received recording state %r", is_recording)
        self._unanswered_service_state_requests = 0  # RESET
        if is_recording == "":  # Special case (ternary value, since None is not supported by OSC)
            self.set_recording_btn_state(disabled=True)
        else:
            self.set_recording_btn_state(pushed=is_recording, disabled=False)

    @osc.address_method("/receive_recording_state")
    @safe_catch_unhandled_exception
    def receive_recording_state(self, is_recording):
        # print(">>>>> app receive_recording_state", repr(is_recording))
        self._schedule_once(self._receive_recording_state, is_recording)

    # SERVICE FEEDBACKS AND DAEMONIZATION #

    def should_daemonize_service(self):  # OVERRIDE THIS TO FETCH USER SETTINGS
        """Return True to let recorder service survive when GUI application gets closed"""
        return False

    def switch_daemonize_service(self, value):
        self.service_controller.switch_daemonize_service(value)

    @osc.address_method("/log_output")
    @safe_catch_unhandled_exception
    def _post_log_output(self, msg):
        self._schedule_once(self.log_output, msg)

    def log_output(self, msg, *args, **kwargs):  # OVERRIDE THIS TO DISPLAY OUTPUT
        pass  # Do nothing by default
