# This file is part of Witness Angel Components
# SPDX-FileCopyrightText: Copyright Prolifik SARL
# SPDX-License-Identifier: GPL-2.0-or-later

import logging
import os
import subprocess

import sys

from ._base_service_controller import ServiceControllerBase
from ..default_settings import WAIT_TIME_MULTIPLIER

WA_SERVICE_SCRIPT = os.getenv("WA_SERVICE_SCRIPT")


logger = logging.getLogger(__name__)


class ServiceController(ServiceControllerBase):

    _subprocess = None

    def start_service(self):
        assert WA_SERVICE_SCRIPT is not None, repr(WA_SERVICE_SCRIPT)
        params = WA_SERVICE_SCRIPT.split("|")
        # self._subprocess might already exist but have crashed
        command = [sys.executable] + params
        cwd = os.path.dirname(params[0] if params else sys.executable) or None
        logger.info("GUI is launching service via Popen command %r, in cwd %r", command, cwd)
        self._subprocess = subprocess.Popen(command, shell=False, cwd=cwd)

    def stop_service(self):
        self._send_message("/stop_server")
        if self._subprocess:  # Else, service already existed at App launch... give up
            try:
                self._subprocess.wait(timeout=10 * WAIT_TIME_MULTIPLIER)
            except subprocess.TimeoutExpired:
                logger.error("Service subprocess didn't exit gracefully, we kill it now")
                self._subprocess.kill()
