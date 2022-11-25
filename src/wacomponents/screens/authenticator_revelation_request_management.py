import logging
from pathlib import Path

from jsonrpc_requests import JSONRPCError
from kivy.factory import Factory
from kivy.lang import Builder
from kivy.properties import ObjectProperty
from kivymd.uix.button import MDFlatButton
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.tab import MDTabsBase

from wacomponents.i18n import tr
from wacomponents.screens.base import WAScreenName, WAScreenBase
from wacomponents.utilities import (
    format_revelation_request_label,
    format_keypair_label,
    format_authenticator_label,
    COLON,
    LINEBREAK,
    format_cryptainer_label,
    shorten_uid,
)
from wacomponents.widgets.layout_components import GrowingAccordion, build_fallback_information_box
from wacomponents.widgets.popups import (
    dialog_with_close_button,
    close_current_dialog,
    display_info_snackbar,
    help_text_popup,
    safe_catch_unhandled_exception_and_display_popup,
    display_info_toast,
)
from wacryptolib.cipher import encrypt_bytestring
from wacryptolib.exceptions import KeyLoadingError, KeyDoesNotExist, KeystoreDoesNotExist, AuthenticationError
from wacryptolib.keygen import load_asymmetric_key_from_pem_bytestring
from wacryptolib.keystore import load_keystore_metadata, FilesystemKeystore
from wacryptolib.trustee import TrusteeApi
from wacryptolib.utilities import load_from_json_bytes, dump_to_json_bytes

Builder.load_file(str(Path(__file__).parent / "authenticator_revelation_request_management.kv"))


logger = logging.getLogger(__name__)

# FIXME RENAME THIS FILE AND KV FILE to authenticator_decryption_request_management.py

# FIXME IN ALL FILES @Francinette:
# - do not use "Error calling method" as message, it means nothing
# - protect public callbacks with @safe_catch_unhandled_exception_and_display_popup
# - use an auto-close in popup callback declaration, not in the handler itself
# - do not intercept exceptions that can't be treated, just let @safe_catch_unhandled_exception_and_display_popup display their snackbar


class Tab(MDFloatLayout, MDTabsBase):
    """Class implementing content for a tab."""


class SymkeyDecryptionStatus:  # FIXME name this enum more precisely, unless we then use it elsewhere?
    DECRYPTED = "DECRYPTED"
    PRIVATE_KEY_MISSING = "PRIVATE KEY MISSING"
    CORRUPTED = "CORRUPTED"
    MISMATCH = "METADATA MISMATCH"
    PENDING = "PENDING"


class AuthenticatorRevelationRequestManagementScreen(WAScreenBase):
    index = 0
    selected_authenticator_dir = ObjectProperty(None, allownone=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def go_to_home_screen(self):  # Fixme deduplicate and push to App!
        self.manager.current = WAScreenName.authenticator_management

    def _display_single_remote_revelation_request(self, status, revelation_request):

        revelationRequestEntry = Factory.revelationRequestEntry()

        revelation_request_label = format_revelation_request_label(
            revelation_request_uid=revelation_request["revelation_request_uid"],
            revelation_request_creation_datetime=revelation_request["created_at"],
        )

        revelationRequestEntry.title = tr._(revelation_request_label)

        target_public_authenticator_label = format_authenticator_label(
            authenticator_owner=revelation_request["target_public_authenticator"]["keystore_owner"],
            keystore_uid=revelation_request["target_public_authenticator"]["keystore_uid"],
        )

        response_key_label = format_keypair_label(
            keychain_uid=revelation_request["revelation_response_keychain_uid"],
            key_algo=revelation_request["revelation_response_key_algo"],
        )

        _displayed_values = dict(
            target_public_authenticator_label=target_public_authenticator_label,
            request_description=revelation_request["revelation_request_description"],
            response_key_label=response_key_label,
        )
        revelation_request_summary_text = (
            tr._("Authenticator")
            + COLON()
            + _displayed_values["target_public_authenticator_label"]
            + LINEBREAK
            + tr._("Description")
            + COLON()
            + _displayed_values["request_description"]
            + LINEBREAK
            + tr._("Local response key")
            + COLON()
            + _displayed_values["response_key_label"]
        )

        revelationRequestEntry.revelation_request_summary.text = revelation_request_summary_text

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

            revelationRequestEntry.symkeys_decryption.add_widget(symkey_decryption_item)

        if status == SymkeyDecryptionStatus.PENDING:
            gridButtons = Factory.GridButtons()

            def reject_request_callback(widget, revelation_request=revelation_request):
                self.open_dialog_reject_request(revelation_request=revelation_request)

            def accept_request_callback(widget, revelation_request=revelation_request):
                self.open_dialog_accept_request(revelation_request=revelation_request)

            gridButtons.rejected_button.bind(on_press=reject_request_callback)
            gridButtons.accepted_button.bind(on_press=accept_request_callback)

            revelationRequestEntry.entry_grid.add_widget(gridButtons)

        return revelationRequestEntry

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

    def display_remote_revelation_request(self, revelation_requests_per_status_list):  # FIXME rename

        logger.debug("Displaying remote decryption requests")

        tab_per_status = dict(
            PENDING=self.ids.pending_revelation_request,
            REJECTED=self.ids.rejected_revelation_request,
            ACCEPTED=self.ids.accepted_revelation_request,
        )

        for status, revelation_requests in revelation_requests_per_status_list.items():

            if not revelation_requests:
                fallback_info_box = build_fallback_information_box(tr._("No authorization request"))
                tab_per_status[status].add_widget(fallback_info_box)
                continue

            scroll = Factory.WAVerticalScrollView()
            root = GrowingAccordion(orientation="vertical", size_hint=(1, None), height=self.height)

            revelation_requests.sort(key=lambda request: request["created_at"], reverse=True)
            for revelation_request in revelation_requests:
                revelation_request_entry = self._display_single_remote_revelation_request(
                    status=status, revelation_request=revelation_request
                )
                root.add_widget(revelation_request_entry)

            root.select(root.children[-1])  # Open FIRST entry
            scroll.add_widget(root)
            tab_per_status[status].add_widget(scroll)

    @staticmethod
    def sort_list_revelation_request_per_status(authenticator_revelation_request_list):
        DECRYPTION_REQUEST_STATUSES = ["PENDING", "ACCEPTED", "REJECTED"]  # KEEP IN SYNC with WASERVER
        revelation_requests_per_status = {status: [] for status in DECRYPTION_REQUEST_STATUSES}

        for revelation_request in authenticator_revelation_request_list:
            revelation_requests_per_status[revelation_request["revelation_request_status"]].append(revelation_request)
        return revelation_requests_per_status

    def get_revelation_request_list_per_status(self):  # FIXME NAMING
        authenticator_path = self.selected_authenticator_dir
        revelation_requests_per_status_list = None
        authenticator_metadata = load_keystore_metadata(authenticator_path)
        keystore_uid = authenticator_metadata["keystore_uid"]
        gateway_proxy = self._app.get_gateway_proxy()
        try:
            authenticator_revelation_request_list = gateway_proxy.list_authenticator_revelation_requests(
                authenticator_keystore_secret=authenticator_metadata["keystore_secret"],
                authenticator_keystore_uid=keystore_uid,
            )
            revelation_requests_per_status_list = self.sort_list_revelation_request_per_status(
                authenticator_revelation_request_list
            )
            message = tr._("Authorization requests were updated")

        except KeystoreDoesNotExist:
            message = tr._("Authenticator does not exist in remote registry")

        except AuthenticationError:
            message = tr._("The keystore secret of authenticator is not valid")

        except (JSONRPCError, OSError) as exc:  # FIXME factorize this!
            logger.error("Error calling gateway server: %r", exc)
            message = tr._("Error querying gateway server, please check its url and you connectivity")

        return revelation_requests_per_status_list, message

    @safe_catch_unhandled_exception_and_display_popup
    def fetch_and_display_revelation_requests(self):

        self.ids.tabs.switch_tab(self.ids.tabs.get_tab_list()[0])  # Return to first Tab

        self.ids.pending_revelation_request.clear_widgets()
        self.ids.rejected_revelation_request.clear_widgets()
        self.ids.accepted_revelation_request.clear_widgets()

        def resultat_callable(result, *args, **kwargs):  # FIXME CHANGE THIS NAME
            revelation_requests_per_status_list, message = result
            if revelation_requests_per_status_list is None:
                display_info_snackbar(message)
            else:
                display_info_toast(message)
                self.display_remote_revelation_request(
                    revelation_requests_per_status_list=revelation_requests_per_status_list
                )

        self._app._offload_task_with_spinner(self.get_revelation_request_list_per_status, resultat_callable)

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
        self.fetch_and_display_revelation_requests()

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
        self.fetch_and_display_revelation_requests()

    def display_help_popup(self):
        authenticator_revelation_request_management_help_text = (
            tr._(
                """This page summarizes the authorization requests that have been sent to your authenticator, in order to decrypt some remote containers."""
            )
            + LINEBREAK * 2
            + tr._(
                """Requests can be freely rejected. Else, to accept them, you must input your passphrase, which will be used to load your private keys and generate authorization tokens for the requester."""
            )
            + LINEBREAK * 2
            + tr._(
                """For now, it is not possible to change the status of a request which has been accepted or rejected."""
            )
        )

        help_text_popup(
            title=tr._("Remote authorization requests page"), text=authenticator_revelation_request_management_help_text
        )
