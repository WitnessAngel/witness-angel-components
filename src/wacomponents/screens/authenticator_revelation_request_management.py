# This file is part of Witness Angel Components
# SPDX-FileCopyrightText: Copyright Prolifik SARL
# SPDX-License-Identifier: GPL-2.0-or-later

import logging
from pathlib import Path

from jsonrpc_requests import JSONRPCError
from kivy.lang import Builder
from kivy.properties import ObjectProperty
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.tab import MDTabsBase

from wacomponents.i18n import tr
from wacomponents.screens.base import WAScreenName, WAScreenBase
from wacomponents.utilities import (
    format_revelation_request_label,
    LINEBREAK,
)
from wacomponents.widgets.popups import (
    display_info_snackbar,
    help_text_popup,
    safe_catch_unhandled_exception_and_display_popup,
    display_info_toast,
)
from wacryptolib.exceptions import KeystoreDoesNotExist, AuthenticationError
from wacryptolib.keystore import load_keystore_metadata

Builder.load_file(str(Path(__file__).parent / "authenticator_revelation_request_management.kv"))


logger = logging.getLogger(__name__)


class Tab(MDFloatLayout, MDTabsBase):
    """Class implementing content for a tab as a FloatLayout."""


class AuthenticatorRevelationRequestManagementScreen(WAScreenBase):

    selected_authenticator_dir = ObjectProperty(None, allownone=True)


    def go_to_home_screen(self):  # Fixme deduplicate and push to App!
        self.manager.current = WAScreenName.authenticator_management

    def _display_remote_revelation_request_(self, revelation_requests_per_status_dict):

        logger.debug("Displaying remote decryption requests")

        tab_per_status = dict(
            PENDING=self.ids.decryption_request_pending_table,
            REJECTED=self.ids.decryption_request_rejected_table,
            ACCEPTED=self.ids.decryption_request_accepted_table,
        )

        # CLEANUP
        for tab in tab_per_status.values():
            tab.data = []

        for status, revelation_requests in revelation_requests_per_status_dict.items():
            recycleview_data = []

            revelation_requests.sort(key=lambda request: request["created_at"], reverse=True)
            for revelation_request in revelation_requests:

                revelation_request_label = format_revelation_request_label(
                    revelation_request_description=revelation_request["revelation_request_description"],
                    revelation_request_creation_datetime=revelation_request["created_at"],
                )

                symkey_decryption_request_count = len(revelation_request["symkey_decryption_requests"])
                symkey_decryption_request_count_label = tr._("Symkey decryption requests: %d") % symkey_decryption_request_count

                def _specific_go_to_details_page_callback(status=status, revelation_request=revelation_request):
                    detail_screen = self.manager.get_screen(WAScreenName.authenticator_revelation_request_detail)
                    detail_screen.setup_revelation_request_details(
                        status=status, revelation_request=revelation_request
                    )
                    self.manager.current = WAScreenName.authenticator_revelation_request_detail

                recycleview_data.append({
                        "text": revelation_request_label,
                        "secondary_text": symkey_decryption_request_count_label,
                        "information_callback": _specific_go_to_details_page_callback,
                    })

            tab_per_status[status].data = recycleview_data

    @staticmethod
    def sort_list_revelation_request_per_status(authenticator_revelation_request_list):
        DECRYPTION_REQUEST_STATUSES = ["PENDING", "ACCEPTED", "REJECTED"]  # KEEP IN SYNC with WASERVER
        revelation_requests_per_status = {status: [] for status in DECRYPTION_REQUEST_STATUSES}

        for revelation_request in authenticator_revelation_request_list:
            revelation_requests_per_status[revelation_request["revelation_request_status"]].append(revelation_request)
        return revelation_requests_per_status

    def _fetch_revelation_requests_sorted_by_status(self):
        authenticator_path = self.selected_authenticator_dir
        revelation_requests_per_status_dict = None
        authenticator_metadata = load_keystore_metadata(authenticator_path)
        keystore_uid = authenticator_metadata["keystore_uid"]
        gateway_proxy = self._app.get_gateway_proxy()
        try:
            authenticator_revelation_request_list = gateway_proxy.list_authenticator_revelation_requests(
                authenticator_keystore_secret=authenticator_metadata["keystore_secret"],
                authenticator_keystore_uid=keystore_uid,
            )
            revelation_requests_per_status_dict = self.sort_list_revelation_request_per_status(
                authenticator_revelation_request_list
            )
            message = tr._("Authorization requests were updated")  # FIXME overrides the decryption success toast, how to handle that?

        except KeystoreDoesNotExist:
            message = tr._("Authenticator does not exist in remote registry")

        except AuthenticationError:
            message = tr._("The keystore secret of authenticator is not valid")

        except (JSONRPCError, OSError) as exc:  # FIXME factorize this!
            logger.error("Error calling gateway server: %r", exc)
            message = tr._("Error querying gateway server, please check its url and your connectivity")

        return revelation_requests_per_status_dict, message

    @safe_catch_unhandled_exception_and_display_popup
    def fetch_and_display_revelation_requests(self):

        self.ids.tabs.switch_tab(self.ids.tabs.get_tab_list()[0])  # Return to first Tab

        def resultat_callable(result, *args, **kwargs):  # FIXME CHANGE THIS NAME
            revelation_requests_per_status_dict, message = result
            if revelation_requests_per_status_dict is None:
                display_info_snackbar(message)
            else:
                display_info_toast(message)
            # In any case refresh the displayed list!
            self._display_remote_revelation_request_(
                revelation_requests_per_status_dict=revelation_requests_per_status_dict or {}
            )

        self._app._offload_task_with_spinner(self._fetch_revelation_requests_sorted_by_status, resultat_callable)

    def display_help_popup(self):
        authenticator_revelation_request_management_help_text = (
            tr._(
                """This page summarizes the authorization requests that have been sent to the selected authenticator, by people wishing to decrypt some of their containers."""
            )
            + LINEBREAK * 2
            + tr._(
                """These requests can be freely rejected. Else, to accept them, you must input your passphrase, which will be used to load your private keys and generate authorization tokens for the requester."""
            )
            + LINEBREAK * 2
            + tr._(
                """For now, it is not possible to change the status of a request which has been accepted or rejected."""
            )
        )

        help_text_popup(
            title=tr._("Authorization requests page"), text=authenticator_revelation_request_management_help_text
        )
