
import subprocess

import os
import sys
from kivy.logger import Logger as logger

from ._base_service_controller import ServiceControllerBase

WA_SERVICE_SCRIPT = os.getenv("WA_SERVICE_SCRIPT")


class ServiceController(ServiceControllerBase):

    _subprocess = None

    def start_service(self):
        assert WA_SERVICE_SCRIPT, WA_SERVICE_SCRIPT
        # "self._subprocess" might already exist but have crashed
        self._subprocess = subprocess.Popen(
            [sys.executable, WA_SERVICE_SCRIPT],
            shell=False,
            cwd=os.path.dirname(WA_SERVICE_SCRIPT),
        )

    def stop_service(self):
        self._send_message("/stop_server")
        if self._subprocess:  # Else, service already existed at App launch... give up
            try:
                self._subprocess.wait(timeout=40)
            except subprocess.TimeoutExpired:
                logger.error("Service subprocess didn't exit gracefully, we kill it now")
                self._subprocess.kill()
