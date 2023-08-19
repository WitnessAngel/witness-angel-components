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
from wacomponents.widgets.popups import dialog_with_close_button, display_info_snackbar, close_current_dialog, \
    safe_catch_unhandled_exception_and_display_popup, display_info_toast
from wacryptolib.cipher import encrypt_bytestring
from wacryptolib.exceptions import KeyDoesNotExist, KeyLoadingError
from wacryptolib.keygen import load_asymmetric_key_from_pem_bytestring
from wacryptolib.keystore import FilesystemKeystore, load_keystore_metadata
from wacryptolib.trustee import TrusteeApi
from wacryptolib.utilities import load_from_json_bytes, dump_to_json_bytes

Builder.load_file(str(Path(__file__).parent / "authenticator_revelation_request_detail.kv"))

logger = logging.getLogger(__name__)

# FIXME RENAME THIS FILE AND KV FILE to decryption_request_detail.py (and later revelation_request_visualization.py) ?


class AuthenticatorRevelationRequestDetailScreen(WAScreenBase):
    def go_to_previous_screen(self):
        self.manager.current = WAScreenName.authenticator_revelation_request_management

    def setup_revelation_request_details(self, status, revelation_request):

        self.status = status
        self.revelation_request = revelation_request

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

        recycleview_data = []

        for index, symkey_decryption in enumerate(revelation_request["symkey_decryption_requests"], start=1):

            symkey_decryption_label1 = tr._("Key of container {short_cryptainer_uid}").format(
                key_index=index, short_cryptainer_uid=shorten_uid(symkey_decryption["cryptainer_uid"])
            )
            symkey_decryption_label2 = format_cryptainer_label(cryptainer_name=symkey_decryption["cryptainer_name"])

            '''
            symkey_decryption_item = Factory.WAIconListItemEntry(
                text=symkey_decryption_label1, secondary_text=symkey_decryption_label2
            )  # FIXME RENAME THIS
            '''

            def _specific_information_popup_callback(symkey_decryption=symkey_decryption):
                self.show_symkey_decryption_details(symkey_decryption=symkey_decryption)

            recycleview_data.append({
                # "unique_identifier": cryptainer_uid,
                "text": symkey_decryption_label1,
                "secondary_text": symkey_decryption_label2,
                "information_callback": _specific_information_popup_callback,
            })

        #print(">>>>>> symkey_decryption_request_table recycleview_data:", recycleview_data)
        self.ids.symkey_decryption_request_table.data = recycleview_data

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

    def open_dialog_accept_request(self):
        revelation_request = self.revelation_request

        logger.debug("Opening dialog to accept decryption request")

        content = Factory.PassphraseRequestForm()
        content.description = tr._("This will allow unmasking the requested symkey parts")

        dialog = dialog_with_close_button(
            close_btn_label=tr._("Cancel"),
            title=tr._("Enter your authenticator passphrase"),
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(
                    text=tr._("Accept"),
                    on_release=lambda *args: (
                        close_current_dialog(),
                        self.accept_revelation_request(
                            passphrase=dialog.content_cls.ids.passphrase_input.text, revelation_request=revelation_request
                        ),
                    ),
                )
            ],
        )

    def open_dialog_reject_request(self):
        revelation_request = self.revelation_request

        logger.debug("Opening dialog to reject decryption request")

        dialog_with_close_button(
            close_btn_label=tr._("Cancel"),
            title=tr._("Do you want to reject this request?"),
            type="simple",
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

    @safe_catch_unhandled_exception_and_display_popup
    def accept_revelation_request(self, passphrase, revelation_request):
        # USE THIS FORM BEFORE :                text=tr._("Confirm removal"), on_release=lambda *args: (
        #                         close_current_dialog(), self.delete_keystores(keystore_uids=keystore_uids))

        revelation_request_uid = revelation_request["revelation_request_uid"]
        logger.info("Accepting decryption request %s", revelation_request_uid)

        authenticator_metadata = load_keystore_metadata(keystore_dir=self.selected_authenticator_dir)
        filesystem_keystore = FilesystemKeystore(self.selected_authenticator_dir)
        trustee_api = TrusteeApi(keystore=filesystem_keystore)
        symkey_decryption_results = []

        # FIXME check passphrase first and report error, instead of leaving "abnormal error" flowing to safe_catch_unhandled_exception_and_display_popup

        for symkey_decryption in revelation_request["symkey_decryption_requests"]:
            decryption_status = SymkeyDecryptionStatus.DECRYPTED
            keychain_uid = symkey_decryption["target_public_authenticator_key"]["keychain_uid"]
            cipher_algo = symkey_decryption["target_public_authenticator_key"]["key_algo"]
            passphrases = [passphrase]
            cipherdict = load_from_json_bytes(symkey_decryption["symkey_decryption_request_data"])

            try:

                key_struct_bytes = trustee_api.decrypt_with_private_key(
                    keychain_uid=keychain_uid, cipher_algo=cipher_algo, cipherdict=cipherdict, passphrases=passphrases
                )

            except KeyDoesNotExist:
                decryption_status = SymkeyDecryptionStatus.PRIVATE_KEY_MISSING

            except KeyLoadingError:
                display_info_snackbar(tr._("Loading of authenticator private key failed (wrong passphrase?)"))
                return  # Abort everything, since the same passphrase is used for all Authenticator keys anyway...

            # We encrypt teh response with the provided response key, this shouldn't fail
            response_key_algo = revelation_request["revelation_response_key_algo"]
            response_public_key = revelation_request["revelation_response_public_key"]
            public_key = load_asymmetric_key_from_pem_bytestring(key_pem=response_public_key, key_algo=cipher_algo)
            response_data_dict = encrypt_bytestring(
                plaintext=key_struct_bytes, cipher_algo=response_key_algo, key_dict=dict(key=public_key)
            )
            response_data = dump_to_json_bytes(response_data_dict)

            symkey_decryption_result = {
                "symkey_decryption_request_data": symkey_decryption["symkey_decryption_request_data"],
                "symkey_decryption_response_data": response_data,
                "symkey_decryption_status": decryption_status,
            }

            symkey_decryption_results.append(symkey_decryption_result)

        gateway_proxy = self._app.get_gateway_proxy()
        gateway_proxy.accept_revelation_request(
            authenticator_keystore_secret=authenticator_metadata["keystore_secret"],
            revelation_request_uid=revelation_request_uid,
            symkey_decryption_results=symkey_decryption_results,
        )

        message = tr._("The decryption request was accepted")

        display_info_toast(message)
        self.go_to_previous_screen()

    @safe_catch_unhandled_exception_and_display_popup
    def reject_revelation_request(self, revelation_request):

        revelation_request_uid = revelation_request["revelation_request_uid"]

        logger.info("Accepting decryption request %s", revelation_request_uid)

        authenticator_metadata = load_keystore_metadata(keystore_dir=self.selected_authenticator_dir)

        gateway_proxy = self._app.get_gateway_proxy()
        gateway_proxy.reject_revelation_request(
            authenticator_keystore_secret=authenticator_metadata["keystore_secret"],
            revelation_request_uid=revelation_request_uid,
        )
        message = tr._("The authorization request was rejected")

        display_info_toast(message)
        self.go_to_previous_screen()