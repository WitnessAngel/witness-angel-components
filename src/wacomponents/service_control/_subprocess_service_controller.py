
import subprocess

import os
import sys
from kivy.logger import Logger as logger

from ._base_service_controller import ServiceControllerBase

WA_SERVICE_SCRIPT = os.getenv("WA_SERVICE_SCRIPT")


class ServiceController(ServiceControllerBase):

    _subprocess = None

    def start_service(self):
        assert WA_SERVICE_SCRIPT is not None, repr(WA_SERVICE_SCRIPT)
        params = WA_SERVICE_SCRIPT.split("|")
        # self._subprocess might already exist but have crashed
        command = [sys.executable] + params
        cwd = os.path.dirname(params[0] if params else sys.executable) or None
        print(">> Starting service via Popen command %r, in cwd %r" % (command, cwd))
        self._subprocess = subprocess.Popen(
            command,
            shell=False,
            cwd=cwd,
        )

    def stop_service(self):
        self._send_message("/stop_server")
        if self._subprocess:  # Else, service already existed at App launch... give up
            try:
                self._subprocess.wait(timeout=40)
            except subprocess.TimeoutExpired:
                logger.error("Service subprocess didn't exit gracefully, we kill it now")
                self._subprocess.kill()
