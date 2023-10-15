import logging
from pathlib import Path

from jsonrpc_requests import JSONRPCError
from kivy.lang import Builder

from wacomponents.i18n import tr
from wacomponents.screens.base import WAScreenName, WAScreenBase
from wacomponents.utilities import (
    format_cryptainer_label,
)
#from wacomponents.widgets.layout_components import build_fallback_information_box
from wacomponents.widgets.popups import dialog_with_close_button, display_info_snackbar, display_info_toast

Builder.load_file(str(Path(__file__).parent / "claimant_revelation_request_management.kv"))

logger = logging.getLogger(__name__)

# FIXME RENAME THIS FILE AND KV FILE to decryption_request_visualization.py (and later revelation_request_visualization.py)


class ClaimantRevelationRequestManagementScreen(WAScreenBase):

    has_been_initialized = False

    def go_to_previous_screen(self):
        self.manager.current = WAScreenName.cryptainer_storage_management

    @staticmethod
    def _list_revelation_requests_per_cryptainer_uid(decryption_requests):
        decryption_requests_per_cryptainer_uid = {}

        for decryption_request in decryption_requests:

            for symkey_decryption_request in decryption_request["symkey_decryption_requests"]:

                decryption_request_copy = {
                    key: value for key, value in decryption_request.items() if key != "symkey_decryption_requests"
                }

                decryption_request_copy["symkey_decryption_request"] = symkey_decryption_request  # SINGLE entry here

                cryptainer_uid = symkey_decryption_request["cryptainer_uid"]
                _decryption_request_for_cryptainer = decryption_requests_per_cryptainer_uid.setdefault(
                    cryptainer_uid, []
                )
                _decryption_request_for_cryptainer.append(decryption_request_copy)

        return decryption_requests_per_cryptainer_uid

    def list_requestor_revelation_requests(self):
        revelation_requestor_uid = self._app.get_wa_device_uid()
        gateway_proxy = self._app.get_gateway_proxy()
        try:
            requestor_revelation_requests = gateway_proxy.list_requestor_revelation_requests(
                revelation_requestor_uid=revelation_requestor_uid
            )
        except (JSONRPCError, OSError):  # FIXME factorize code with snackbar here?
            requestor_revelation_requests = None
        return requestor_revelation_requests

    def conditionally_refresh_decryption_request_list(self):
        if not self.has_been_initialized:
            self.display_decryption_request_list()
            self.has_been_initialized = True

    def display_decryption_request_list(self):  #FIXME rename -> cryptainers display

        logger.debug("Displaying decryption request list")

        #self.ids.list_decryption_request_scrollview.clear_widgets()

        def resultat_callable(requestor_revelation_requests, *args, **kwargs):  # FIXME CHANGE THIS NAME
            if requestor_revelation_requests is None:
                display_info_snackbar(tr._("Network error, please check the gateway url"))
                return

            #if not requestor_revelation_requests:  # FIXME RENAME ALL decryption requests!!!!
                #fallback_info_box = build_fallback_information_box(tr._("No authorization requests found"))
                #self.ids.list_decryption_request_scrollview.add_widget(fallback_info_box)  # FIXME
            #    return

            revelation_requests_per_cryptainer_uid = self._list_revelation_requests_per_cryptainer_uid(
                requestor_revelation_requests
            )

            #display_layout = GrowingAccordion(orientation="vertical", size_hint=(1, None))

            recycleview_data = []  # List of dicts

            # Sorting kinda works, because UUID0 of cryptainers are built by datetime!
            for cryptainer_uid, revelation_requests_with_single_symkey in sorted(
                revelation_requests_per_cryptainer_uid.items(), reverse=True
            ):

                # Fetch cryptainer name from FIRST entry (which MUST exist)
                cryptainer_name = revelation_requests_with_single_symkey[0]["symkey_decryption_request"][
                    "cryptainer_name"
                ]

                cryptainer_label = format_cryptainer_label(
                    cryptainer_name=cryptainer_name, cryptainer_uid=cryptainer_uid
                )

                cryptainer_sublabel = tr._("Authorization requests: %d") % len(revelation_requests_with_single_symkey)

                def _specific_go_to_details_page_callback(  # Capture current loop variables
                        _cryptainer_uid=cryptainer_uid,
                        _cryptainer_label=cryptainer_label,
                        _revelation_requests_with_single_symkey=revelation_requests_with_single_symkey):

                    def go_to_details_page_callback():  # FIXME no need for nested fun here actually!
                        #print("CALLING go_to_details_page_callback() with cryptainer_uid")
                        detail_screen = self.manager.get_screen(WAScreenName.claimant_revelation_request_detail)
                        detail_screen.setup_revelation_request_details(
                            cryptainer_uid=_cryptainer_uid,
                            cryptainer_label=_cryptainer_label,
                            revelation_requests_with_single_symkey=_revelation_requests_with_single_symkey,
                        )
                        self.manager.current = WAScreenName.claimant_revelation_request_detail
                    return go_to_details_page_callback

                #container_item = Factory.ContainerItem(title=tr._("Container") + " " + cryptainer_label)
                ###for i in range(1):
                recycleview_data.append({
                    #"unique_identifier": cryptainer_uid,
                    "text": cryptainer_label,
                    "secondary_text": cryptainer_sublabel,
                    "information_callback": _specific_go_to_details_page_callback(),
                })


                """
                for revelation_request_with_single_symkey in revelation_requests_with_single_symkey:

                    assert (
                        cryptainer_uid
                        == revelation_request_with_single_symkey["symkey_decryption_request"]["cryptainer_uid"]
                    )

                    revelation_request_label1 = format_revelation_request_label(
                        revelation_request_uid=revelation_request_with_single_symkey["revelation_request_uid"],
                        revelation_request_creation_datetime=revelation_request_with_single_symkey["created_at"],
                        keystore_owner=revelation_request_with_single_symkey["target_public_authenticator"][
                            "keystore_owner"
                        ],
                    )

                    revelation_request_label2 = (
                        tr._("Status") + COLON() + revelation_request_with_single_symkey["revelation_request_status"]
                    )

                    target_public_authenticator_label = format_authenticator_label(
                        authenticator_owner=revelation_request_with_single_symkey["target_public_authenticator"][
                            "keystore_owner"
                        ],
                        keystore_uid=revelation_request_with_single_symkey["target_public_authenticator"][
                            "keystore_uid"
                        ],
                    )

                    authenticator_key_algo = revelation_request_with_single_symkey["symkey_decryption_request"][
                        "target_public_authenticator_key"
                    ]["key_algo"]
                    authenticator_keychain_uid = revelation_request_with_single_symkey["symkey_decryption_request"][
                        "target_public_authenticator_key"
                    ]["keychain_uid"]

                    authenticator_key_label = format_keypair_label(
                        keychain_uid=authenticator_keychain_uid, key_algo=authenticator_key_algo
                    )

                    response_key_label = format_keypair_label(
                        keychain_uid=revelation_request_with_single_symkey["revelation_response_keychain_uid"],
                        key_algo=revelation_request_with_single_symkey["revelation_response_key_algo"],
                    )

                    _displayed_values = dict(  # FIXME remove that
                        revelation_request_description=revelation_request_with_single_symkey[
                            "revelation_request_description"
                        ],
                        target_public_authenticator_label=target_public_authenticator_label,
                        response_key_label=response_key_label,
                        symkey_decryption_status=revelation_request_with_single_symkey["symkey_decryption_request"][
                            "symkey_decryption_status"
                        ],
                        authenticator_key_label=authenticator_key_label,
                    )

                    revelation_request_summary_text = (
                        tr._("Description")
                        + COLON()
                        + _displayed_values["revelation_request_description"]
                        + 2 * LINEBREAK
                        + tr._("Authenticator")
                        + COLON()
                        + _displayed_values["target_public_authenticator_label"]
                        + LINEBREAK
                        + tr._("Authenticator key")
                        + COLON()
                        + _displayed_values["authenticator_key_label"]
                        + LINEBREAK
                        + tr._("Local key for response")
                        + COLON()
                        + _displayed_values["response_key_label"]
                        + 2 * LINEBREAK
                        + tr._("Symkey decryption status")
                        + COLON()
                        + _displayed_values["symkey_decryption_status"]
                    )

                    revelation_request_entry = Factory.WAIconListItemEntry(
                        text=revelation_request_label1, secondary_text=revelation_request_label2
                    )
                    """

                """
                    def information_callback(widget, revelation_request_info=revelation_request_summary_text):
                        # We MUST use this "revelation_request_info" parameter to freeze the "variable revelation_request_summary_text"
                        self.show_revelation_request_info(revelation_request_info=revelation_request_info)

                    information_icon = revelation_request_entry.ids.information_icon
                    information_icon.bind(on_press=information_callback)

                    container_item.revelation_requests_list.add_widget(revelation_request_entry)
                    """

                #display_layout.add_widget(container_item)

            #display_layout.select(display_layout.children[-1])  # Open FIRST entry
            self.ids.decryption_request_table.data = recycleview_data
            # FIXME do we need to force refresh of data???
            display_info_toast(tr._("Refreshed authorization requests"))

        self._app._offload_task_with_spinner(self.list_requestor_revelation_requests, resultat_callable)

    def show_revelation_request_info(self, revelation_request_info):

        logger.debug(
            "Displaying single decryption request info"
        )  # FIXME normalize decryption/revelation/aithorization wordings everywhere...

        dialog_with_close_button(
            close_btn_label=tr._("Close"), title=tr._("Authorization request summary"), text=revelation_request_info
        )
