import logging
from concurrent.futures.thread import ThreadPoolExecutor
from configparser import ConfigParser, Error as ConfigParserError

import os
from oscpy.server import ServerClass

from wacomponents.application._common_runtime_support import WaRuntimeSupportMixin
from wacomponents.default_settings import IS_ANDROID, WIP_RECORDING_MARKER, CONTEXT
from wacomponents.logging.handlers import CallbackHandler, safe_catch_unhandled_exception
from wacomponents.recording_toolchain import start_recording_toolchain, stop_recording_toolchain
from wacomponents.service_control import get_osc_server, get_osc_client
from wacomponents.utilities import InterruptableEvent

# os.environ["KIVY_NO_CONSOLELOG"] = "1"  # IMPORTANT

osc, osc_starter_callback = get_osc_server(is_master=False)

# FIXME what happens if exception on remote OSC endpoint ? CRASH!!
# TODO add custom "local trustee resolver"
# TODO add exception swallowers, and logging pushed to frontend app (if present)


logger = logging.getLogger()  # FIXME take a particular logger here!!


if IS_ANDROID:
    from wacomponents.application.android_helpers import preload_java_classes
    preload_java_classes()


@ServerClass
class WaRecorderService(WaRuntimeSupportMixin):
    """
    The background server automatically starts when service script is launched.

    It must be stopped gracefully with a call to "/stop_server", so that current recordings can be properly stored.

    While the server is alive, recordings can be started and stopped several times without problem.
    """

    # CLASS VARIABLES TO BE OVERRIDEN #
    thread_pool_executor: ThreadPoolExecutor = None

    _sock = None
    _recording_toolchain = None
    _status_change_in_progress = False  # Set to True while recording is starting/stopping

    def __init__(self):

        logger.info("Starting service")  # Will not be sent to App (too early)
        osc_starter_callback()  # Opens server port
        self._osc_client = get_osc_client(to_app=True)
        logging.getLogger(None).addHandler(
            CallbackHandler(self._remote_logging_callback)
        )
        self._termination_event = InterruptableEvent()
        logger.info("Service started")

        self.reload_config()

        # Initial setup of service according to persisted config
        try:
            daemonize_service = self.config.getboolean("usersettings", "daemonize_service")  # FIXME is that really "usersettings" here?
        except ConfigParserError:
            daemonize_service = False  # Probably App is just initializing itself
        self.switch_daemonize_service(daemonize_service)

        #import traceback; traceback.print_stack()
        if WIP_RECORDING_MARKER.exists():
            self.start_recording()  # Autorecord e.g. after a restart due to closing of main android Activity

    def _get_cryptoconf(self):
        """Return a wacryptolib-compatible encryption configuration"""
        raise NotImplementedError("_get_cryptoconf()")

    def _build_recording_toolchain(self):
        """Return a valid recording toolchain"""
        raise NotImplementedError("_build_recording_toolchain()")

    def reload_config(self, filename=None):  # FIXME move to generic app ?

        if not filename:
            filename = self.config_file_path

        logger.info(f"Reloading config file {filename}")

        # No NAME here, since named parsers must be Singletons in process!
        config = ConfigParser()
        config.read(str(self.config_defaults_path))  # Default values

        try:
            if not os.path.exists(filename):
                raise FileNotFoundError(filename)
            config.read(str(filename))  # Fails silently if file not found
        except (ConfigParserError, FileNotFoundError) as exc:
            logger.error(
                f"Service: Ignored missing or corrupted config file {filename} ({exc!r})"
            )

        # logger.info(f"Config file {filename} loaded")
        self.config = config

    def _remote_logging_callback(self, msg):
        max_length = 64000  # Beware OSCP server expects max 65535 in input, prevent overflow here
        if len(msg) > max_length:
            msg = msg[:max_length] + "<truncated...>"
        return self._send_message("/log_output", "Service: " + msg)

    def _send_message(self, address, *values):
        #print("Message sent from service to app: %s %s" % (address, values))
        try:
            return self._osc_client.send_message(address, values=values)
        except OSError as exc:
            # NO LOGGING HERE, else it would loop due to custom logging handler
            ##print(
            ##    "{SERVICE} Could not send osc message %s%s to app: %r"
            ##    % (address, values, exc)
            ##)
            return

    def _offload_task(self, method, *args, **kwargs):
        return self.thread_pool_executor.submit(method, *args, **kwargs)

    @osc.address_method("/ping")
    @safe_catch_unhandled_exception
    def ping(self):
        logger.info("Ping successful!")
        self._send_message("/log_output", "Pong")

    @safe_catch_unhandled_exception
    def _offloaded_switch_daemonize_service(self, value):
        value = bool(value)  # Normalize from possible integer
        logger.info("Switching background service persistence to %s", value)
        if IS_ANDROID:
            from jnius import autoclass
            PythonService = autoclass('org.kivy.android.PythonService')
            PythonService.mService.setAutoStopService(not value)
        # Nothing to do for desktop platforms

    @osc.address_method("/switch_daemonize_service")
    @safe_catch_unhandled_exception
    def switch_daemonize_service(self, value):
        return self._offload_task(self._offloaded_switch_daemonize_service, value=value)

    @safe_catch_unhandled_exception
    def _offloaded_start_recording(self, env):
        try:
            if self.is_recording:
                #logger.debug("Ignoring redundant call to service.start_recording()")
                return
            logger.info("Starting offloaded recording")

            if not self._recording_toolchain:
                self._recording_toolchain = self._build_recording_toolchain()  # FIXME handle exceptions instead of None!

            assert self._recording_toolchain
            start_recording_toolchain(self._recording_toolchain)
            logger.info("Offloaded recording started")

            if IS_ANDROID:
                from wacomponents.application.android_helpers import build_notification_channel, build_notification
                build_notification_channel(CONTEXT, "Witness Angel Service")
                notification = build_notification(CONTEXT, title="Sensors are active",
                                                  message="Click to manage Witness Angel state",
                                                  ticker="Witness Angel sensors are active")
                notification_uid = 1
                CONTEXT.startForeground(notification_uid, notification)

        except Exception as exc:
            logger.error("Could not build recording toolchain: %r" % exc)
        finally:
            self._status_change_in_progress = False
            self.broadcast_recording_state()  # Even on error

    @osc.address_method("/start_recording")
    @safe_catch_unhandled_exception
    def start_recording(self, env=None):
        # Fixme - remove "env" parameter if unused?
        self._status_change_in_progress = True
        WIP_RECORDING_MARKER.touch(exist_ok=True)
        self.reload_config()  # Important
        if not self.refresh_checkup_status():
            logger.error("Service failed to start recording because of configuration issues")
            return
        return self._offload_task(self._offloaded_start_recording, env=env)

    @property
    def is_recording(self):
        return bool(
            self._recording_toolchain
            and self._recording_toolchain["sensors_manager"].is_running
        )

    @osc.address_method("/broadcast_recording_state")
    @safe_catch_unhandled_exception
    def broadcast_recording_state(self):
        """
        Broadcasts a TERNARY state, with the special value "" if a status change is in progress
        (since OSC doesn't like None values...)
        """
        if self._status_change_in_progress:
            is_recording = ""  # For ternary value, since None is not supported by OSC
        else:
            is_recording = self.is_recording
        #logger.debug("Broadcasting service state (is_recording=%r)" % is_recording)
        self._send_message("/receive_recording_state", is_recording)

    @safe_catch_unhandled_exception
    def _offloaded_stop_recording(self):
        try:
            if not self.is_recording:
                #logger.debug("Ignoring redundant call to service.stop_recording()")
                return
            logger.info("Stopping recording")
            stop_recording_toolchain(self._recording_toolchain)
            logger.info("Recording stopped")

            if IS_ANDROID:
                CONTEXT.stopForeground(True)  # Does remove notification

        finally:  # Trigger all this even if container flushing failed
            self._recording_toolchain = (
                None
            )  # Will force a reload of config on next recording
            self._status_change_in_progress = False
            self.broadcast_recording_state()

    @osc.address_method("/stop_recording")
    @safe_catch_unhandled_exception
    def stop_recording(self):
        self._status_change_in_progress = True
        try:
            WIP_RECORDING_MARKER.unlink()  # TODO use "missing_ok" asap
        except FileNotFoundError:
            pass
        return self._offload_task(self._offloaded_stop_recording)

    @osc.address_method("/stop_server")
    @safe_catch_unhandled_exception
    def stop_server(self):
        logger.info("Stopping service")

        if self.is_recording:
            logger.info(
                "Recording is in progress, we stop it as part of service shutdown"
            )
            self.stop_recording().result(timeout=30)   # SYNCHRONOUS CALL (but through threadpool still)

        osc.stop_all()
        self._termination_event.set()
        logger.info("Service stopped")

    @safe_catch_unhandled_exception
    def join(self):
        """
        Wait for the termination of the background server
        (meant for use by the main thread of the service process).
        """
        self._termination_event.wait()

