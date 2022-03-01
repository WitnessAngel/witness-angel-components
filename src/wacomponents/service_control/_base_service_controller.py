from wacomponents.service_control import get_osc_client


class ServiceControllerBase:

    _osc_client = None

    def __init__(self):
        self._osc_client = get_osc_client(to_app=False)

    def _send_message(self, address, *values):
        #print("Message sent from app to service: %s %s" % (address, values))
        try:
            return self._osc_client.send_message(address, values=values)
        except ConnectionError:
            pass  # Normal at start of app...
        except Exception as exc:
            print("Could not send osc message %s%s to service: %r" % (address, values, exc))
            return

    def ping(self):
        return self._send_message("/ping")

    def switch_daemonize_service(self, value):
        assert value in (True, False), repr(value)
        self._send_message("/switch_daemonize_service", value)

    def start_recording(self, env=""):
        self._send_message("/start_recording", env)

    def stop_recording(self):
        self._send_message("/stop_recording")

    def broadcast_recording_state(self):
        self._send_message("/broadcast_recording_state")

    def attempt_cryptainer_decryption(self, cryptainer_filepath):  # FIXME unused, pb with transfer of passphrases for now...
        self._send_message("/attempt_cryptainer_decryption", cryptainer_filepath)
