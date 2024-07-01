# This file is part of Witness Angel Components
# SPDX-FileCopyrightText: Copyright Prolifik SARL
# SPDX-License-Identifier: GPL-2.0-or-later

from kivymd.app import MDApp
from kivymd.uix import Screen


class WAScreenName:
    """Common registry for all the screen names to be used in WA applications"""

    # Recorder Screens
    recorder_homepage = "recorder_homepage"
    foreign_keystore_management = "foreign_keystore_management"
    cryptainer_storage_management = "cryptainer_storage_management"
    cryptainer_decryption_process = "cryptainer_decryption_process"
    cryptainer_decryption_result = "cryptainer_decryption_result"
    claimant_revelation_request_creation_form = "claimant_revelation_request_creation_form"
    claimant_revelation_request_management = "claimant_revelation_request_management"
    claimant_revelation_request_detail = "claimant_revelation_request_detail"

    # AUTHENTICATOR Screens
    authenticator_management = "authenticator_management"
    authenticator_creation_form = "authenticator_creation_form"
    authenticator_publication_form = "authenticator_publication_form"
    authenticator_revelation_request_management = "authenticator_revelation_request_management"
    authenticator_revelation_request_detail = "authenticator_revelation_request_detail"


class WAScreenBase(Screen):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._app = MDApp.get_running_app()
