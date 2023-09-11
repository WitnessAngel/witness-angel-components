import logging
from pathlib import Path

from kivy.factory import Factory
from kivy.lang import Builder

from wacomponents.i18n import tr
from wacomponents.screens.base import WAScreenName, WAScreenBase
from wacomponents.utilities import (
    format_revelation_request_label,
    format_authenticator_label,
    format_keypair_label,
    COLON,
    LINEBREAK,
)
from wacomponents.widgets.popups import dialog_with_close_button

Builder.load_file(str(Path(__file__).parent / "claimant_revelation_request_detail.kv"))

logger = logging.getLogger(__name__)

# FIXME RENAME THIS FILE AND KV FILE to decryption_request_detail.py (and later revelation_request_visualization.py) ?


class ClaimantRevelationRequestDetailScreen(WAScreenBase):
    def go_to_previous_screen(self):
        self.manager.current = WAScreenName.claimant_revelation_request_management

    def setup_revelation_request_details(
            self,
            cryptainer_uid,
            cryptainer_label,
            revelation_requests_with_single_symkey):
        self.cryptainer_uid = cryptainer_uid
        self.cryptainer_label = cryptainer_label
        self._display_decryption_request_list(revelation_requests_with_single_symkey)

    def _display_decryption_request_list(self, revelation_requests_with_single_symkey):

        logger.debug("Displaying decryption request list for %s", self.cryptainer_label)

        self.ids.revelation_requests_list.clear_widgets()  # FIXME add fallback entry ?

        for revelation_request_with_single_symkey in revelation_requests_with_single_symkey:

            assert (
                self.cryptainer_uid
                == revelation_request_with_single_symkey["symkey_decryption_request"]["cryptainer_uid"]
            ), (self.cryptainer_uid, revelation_request_with_single_symkey["symkey_decryption_request"]["cryptainer_uid"])

            revelation_request_label1 = format_revelation_request_label(
                revelation_request_description=revelation_request_with_single_symkey["revelation_request_description"],
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

            def information_callback(widget, revelation_request_info=revelation_request_summary_text):
                # We MUST use this "revelation_request_info" parameter to freeze the "variable revelation_request_summary_text"
                self.show_revelation_request_info(revelation_request_info=revelation_request_info)

            information_icon = revelation_request_entry.ids.information_icon
            information_icon.bind(on_press=information_callback)

            self.ids.revelation_requests_list.add_widget(revelation_request_entry)


    def show_revelation_request_info(self, revelation_request_info):

        logger.debug(
            "Displaying single decryption request info"
        )  # FIXME normalize decryption/revelation/aithorization wordings everywhere...

        dialog_with_close_button(
            close_btn_label=tr._("Close"), title=tr._("Authorization request summary"), text=revelation_request_info
        )
