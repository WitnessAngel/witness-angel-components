import logging
from pathlib import Path

from jsonrpc_requests import JSONRPCError
from kivy.factory import Factory
from kivy.lang import Builder
from kivymd.uix.button import MDFlatButton

from wacomponents.i18n import tr
from wacomponents.screens.authenticator_revelation_request_management import SymkeyDecryptionStatus
from wacomponents.screens.base import WAScreenName, WAScreenBase
from wacomponents.utilities import (
    format_revelation_request_label,
    format_authenticator_label,
    format_keypair_label,
    COLON,
    LINEBREAK,
    format_cryptainer_label, shorten_uid,
)
from wacomponents.widgets.layout_components import GrowingAccordion, build_fallback_information_box
from wacomponents.widgets.popups import dialog_with_close_button, display_info_snackbar, close_current_dialog

Builder.load_file(str(Path(__file__).parent / "authenticator_revelation_request_detail.kv"))

logger = logging.getLogger(__name__)

# FIXME RENAME THIS FILE AND KV FILE to decryption_request_detail.py (and later revelation_request_visualization.py) ?


class AuthenticatorRevelationRequestDetailScreen(WAScreenBase):
    def go_to_previous_screen(self):
        self.manager.current = WAScreenName.authenticator_revelation_request_management

    def setup_revelation_request_details(self,
        status, revelation_request):

        self.action_buttons_are_enabled = (status == SymkeyDecryptionStatus.PENDING)

        revelation_request_label = format_revelation_request_label(
            revelation_request_uid=revelation_request["revelation_request_uid"],
            revelation_request_creation_datetime=revelation_request["created_at"],
        )
        self.revelation_request_label = revelation_request_label

        target_public_authenticator_label = format_authenticator_label(
            authenticator_owner=revelation_request["target_public_authenticator"]["keystore_owner"],
            keystore_uid=revelation_request["target_public_authenticator"]["keystore_uid"],
        )

        response_key_label = format_keypair_label(
            keychain_uid=revelation_request["revelation_response_keychain_uid"],
            key_algo=revelation_request["revelation_response_key_algo"],
        )

        revelation_request_summary_text = (
            tr._("Authenticator")
            + COLON()
            + target_public_authenticator_label
            + LINEBREAK
            + tr._("Description")
            + COLON()
            + revelation_request["revelation_request_description"]
            + LINEBREAK
            + tr._("Local response key")
            + COLON()
            + response_key_label
        )
        self.revelation_request_summary_text = revelation_request_summary_text

        print(">>>>>self.ids.symkey_decryption_request_list", self.ids.symkey_decryption_request_list)
        self.ids.symkey_decryption_request_list.clear_widgets()

        for index, symkey_decryption in enumerate(revelation_request["symkey_decryption_requests"], start=1):

            symkey_decryption_label1 = tr._("Key of container {short_cryptainer_uid}").format(
                key_index=index, short_cryptainer_uid=shorten_uid(symkey_decryption["cryptainer_uid"])
            )
            symkey_decryption_label2 = format_cryptainer_label(cryptainer_name=symkey_decryption["cryptainer_name"])

            symkey_decryption_item = Factory.WAIconListItemEntry(
                text=symkey_decryption_label1, secondary_text=symkey_decryption_label2
            )  # FIXME RENAME THIS

            def information_callback(widget, symkey_decryption=symkey_decryption):
                self.show_symkey_decryption_details(symkey_decryption=symkey_decryption)

            information_icon = symkey_decryption_item.ids.information_icon
            information_icon.bind(on_press=information_callback)

            self.ids.symkey_decryption_request_list.add_widget(symkey_decryption_item)

    def show_symkey_decryption_details(self, symkey_decryption):  # FIXME rename method

        logger.debug("Showing details of single symkey decryption request")

        authenticator_key_algo = symkey_decryption["target_public_authenticator_key"]["key_algo"]
        authenticator_keychain_uid = symkey_decryption["target_public_authenticator_key"]["keychain_uid"]

        authenticator_key_label = format_keypair_label(
            keychain_uid=authenticator_keychain_uid, key_algo=authenticator_key_algo
        )

        _displayed_values = dict(  # FIXME remove this useless dict! and others too!
            authenticator_key_label=authenticator_key_label,
            cryptainer_metadata=symkey_decryption["cryptainer_metadata"],
            symkey_decryption_status=symkey_decryption["symkey_decryption_status"],
        )

        symkey_decryption_info_text = (
            tr._("Concerned authenticator key")
            + COLON()
            + _displayed_values["authenticator_key_label"]
            + LINEBREAK
            + tr._("Cryptainer metadata")
            + COLON()
            + str(_displayed_values["cryptainer_metadata"])
            + LINEBREAK
            + tr._("Decryption status")
            + COLON()
            + _displayed_values["symkey_decryption_status"]
        )

        dialog_with_close_button(
            close_btn_label=tr._("Close"), title=tr._("Symkey decryption request"), text=symkey_decryption_info_text
        )

    def open_dialog_accept_request(self, revelation_request):

        logger.debug("Opening dialog to accept decryption request")

        dialog = dialog_with_close_button(
            close_btn_label=tr._("Cancel"),
            title=tr._("Enter your authenticator passphrase"),
            type="custom",
            content_cls=Factory.AddPersonalPassphraseContent(),
            buttons=[
                MDFlatButton(
                    text=tr._("Accept"),
                    on_release=lambda *args: (
                        close_current_dialog(),
                        self.accept_revelation_request(
                            passphrase=dialog.content_cls.ids.passphrase.text, revelation_request=revelation_request
                        ),
                    ),
                )
            ],
        )

    def open_dialog_reject_request(self, revelation_request):

        logger.debug("Opening dialog to reject decryption request")

        dialog_with_close_button(
            close_btn_label=tr._("Cancel"),
            title=tr._("Do you want to reject this request?"),
            type="custom",
            buttons=[
                MDFlatButton(
                    text=tr._("Reject"),
                    on_release=lambda *args: (
                        close_current_dialog(),
                        self.reject_revelation_request(revelation_request=revelation_request),
                    ),
                )
            ],
        )
