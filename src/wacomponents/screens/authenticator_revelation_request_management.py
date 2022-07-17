from pathlib import Path
from textwrap import dedent

from kivy.lang import Builder
from kivy.properties import ObjectProperty, BooleanProperty, StringProperty
from kivy.uix.accordion import Accordion

from kivymd.app import MDApp
from kivy.factory import Factory
from kivymd.uix.button import MDFlatButton
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.screen import Screen
from kivymd.uix.tab import MDTabsBase
from wacomponents.widgets.layout_components import GrowingAccordion, build_fallback_information_box
from wacryptolib.cipher import encrypt_bytestring
from wacryptolib.exceptions import KeyLoadingError, KeyDoesNotExist, KeystoreDoesNotExist, \
    AuthenticationError, ExistenceError
from wacryptolib.keygen import load_asymmetric_key_from_pem_bytestring
from wacryptolib.keystore import load_keystore_metadata, FilesystemKeystore
from wacryptolib.trustee import TrusteeApi
from wacryptolib.utilities import load_from_json_bytes, dump_to_json_bytes

from wacomponents.i18n import tr
from wacomponents.utilities import shorten_uid
from wacomponents.widgets.popups import dialog_with_close_button, close_current_dialog, display_info_snackbar, \
    help_text_popup, safe_catch_unhandled_exception_and_display_popup

Builder.load_file(str(Path(__file__).parent / 'authenticator_revelation_request_management.kv'))


# FIXME RENAME THIS FILE AND KV FILE to authenticator_decryption_request_management.py

# FIXME IN ALL FILES @Francinette:
# - do not use "Error calling method" as message, it means nothing
# - protect public callbacks with @safe_catch_unhandled_exception_and_display_popup
# - use an auto-close in popup callback declaration, not in the handler itself
# - do not intercept exceptions that can't be treated, just let @safe_catch_unhandled_exception_and_display_popup display their snackbar


class Tab(MDFloatLayout, MDTabsBase):
    """Class implementing content for a tab."""


class SymkeyDecryptionStatus:  # FIXME name this enum more precisely, unless we then use it elsewhere?
    DECRYPTED = 'DECRYPTED'
    PRIVATE_KEY_MISSING = 'PRIVATE KEY MISSING'
    CORRUPTED = 'CORRUPTED'
    MISMATCH = 'METADATA MISMATCH'
    PENDING = 'PENDING'


class AuthenticatorRevelationRequestManagementScreen(Screen):
    index = 0
    selected_authenticator_dir = ObjectProperty(None, allownone=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._app = MDApp.get_running_app()
        self.gateway_proxy = self._app.get_gateway_proxy()

    def go_to_home_screen(self):  # Fixme deduplicate and push to App!
        self.manager.current = "authenticator_selector_screen"

    def _display_single_remote_decryption_request(self, status, decryption_request):

        decryptionRequestEntry = Factory.DecryptionRequestEntry()

        decryptionRequestEntry.title = tr._("Request : {revelation_request_uid}").format(
            revelation_request_uid=decryption_request["revelation_request_uid"])

        _displayed_values = dict(
            target_public_authenticator=decryption_request["target_public_authenticator"]["keystore_owner"],
            requestor_uid=decryption_request["revelation_requestor_uid"],
            request_description=decryption_request["revelation_request_description"],
            response_keychain_uid=shorten_uid(decryption_request["revelation_response_keychain_uid"]),
            response_key_algo=decryption_request["revelation_response_key_algo"]
        )

        decryption_request_summary_text = dedent(tr._("""\
                                    Target Public Authenticator: {target_public_authenticator}
                                    Revelation Requestor ID: {requestor_uid}
                                    Description: {request_description}
                                    Response public key: {response_keychain_uid}({response_key_algo})\
                                """)).format(**_displayed_values)

        decryptionRequestEntry.decryption_request_summary.text = decryption_request_summary_text

        for index, symkey_decryption in enumerate(decryption_request['symkey_decryption_requests'], start=1):
            symkey_decryption_label = tr._("Container N° {key_index}: {Container_uid} "). \
                format(key_index=index, Container_uid=symkey_decryption["cryptainer_uid"])

            symkey_decryption_item = Factory.WAIconListItemEntry(text=symkey_decryption_label)  # FIXME RENAME THIS

            def information_callback(widget, symkey_decryption=symkey_decryption):
                self.show_symkey_decryption_details(symkey_decryption=symkey_decryption)

            information_icon = symkey_decryption_item.ids.information_icon
            information_icon.bind(on_press=information_callback)

            decryptionRequestEntry.symkeys_decryption.add_widget(symkey_decryption_item)

        if status == SymkeyDecryptionStatus.PENDING:
            gridButtons = Factory.GridButtons()

            def reject_request_callback(widget, decryption_request=decryption_request):
                self.open_dialog_reject_request(decryption_request=decryption_request)

            def accept_request_callback(widget, decryption_request=decryption_request):
                self.open_dialog_accept_request(decryption_request=decryption_request)

            gridButtons.rejected_button.bind(on_press=reject_request_callback)
            gridButtons.accepted_button.bind(on_press=accept_request_callback)

            decryptionRequestEntry.entry_grid.add_widget(gridButtons)

        return decryptionRequestEntry

    def show_symkey_decryption_details(self, symkey_decryption):

        _displayed_values = dict(
            key_algo=symkey_decryption["target_public_authenticator_key"]["key_algo"],
            keychain_uid=symkey_decryption["target_public_authenticator_key"]["keychain_uid"],
            cryptainer_uid=symkey_decryption["cryptainer_uid"],
            cryptainer_metadata=symkey_decryption["cryptainer_metadata"],
            symkey_decryption_request_data=symkey_decryption["symkey_decryption_request_data"],
            symkey_decryption_status=symkey_decryption["symkey_decryption_status"]
        )

        symkey_decryption_info_text = dedent(tr._("""\
                                   Cryptainer uid: {cryptainer_uid}
                                   Cryptainer metadata: {cryptainer_metadata}
                                   Key needeed: {keychain_uid}({key_algo})
                                   Decryption status: {symkey_decryption_status}
                               """)).format(**_displayed_values)
        dialog_with_close_button(
            close_btn_label=tr._("Close"),
            title=tr._("Symkey decryption details"),
            text=symkey_decryption_info_text,
        )

    def open_dialog_accept_request(self, decryption_request):
        dialog = dialog_with_close_button(
            close_btn_label=tr._("Cancel"),
            title=tr._("Enter your passphrase"),
            type="custom",
            content_cls=Factory.CheckPassphraseContent(),
            buttons=[
                MDFlatButton(text=tr._("Accept"), on_release=lambda *args: self.accept_revelation_request(
                    passphrase=dialog.content_cls.ids.passphrase.text, decryption_request=decryption_request))],
        )

    def open_dialog_reject_request(self, decryption_request):
        dialog_with_close_button(
            close_btn_label=tr._("Cancel"),
            title=tr._("Do you want to reject this request?"),
            type="custom",
            buttons=[
                MDFlatButton(text=tr._("Reject"), on_release=lambda *args: self.reject_revelation_request(
                    decryption_request=decryption_request))],
        )

    def display_remote_decryption_request(self, list_revelation_requests_per_status):  # TODO change name function
        # TODO add list_decryption_request to parameter of this function
        # why????

        tab_per_status = dict(PENDING=self.ids.pending_decryption_request,
                              REJECTED=self.ids.rejected_decryption_request,
                              ACCEPTED=self.ids.accepted_decryption_request)

        for status, decryption_requests in list_revelation_requests_per_status.items():

            if not decryption_requests:
                fallback_info_box = build_fallback_information_box(tr._("No decryption request"))
                tab_per_status[status].add_widget(fallback_info_box)
                continue

            scroll = Factory.WAVerticalScrollView()
            root = GrowingAccordion(orientation='vertical', size_hint=(1, None), height=self.height)
            for decryption_request in decryption_requests:
                decryption_request_entry = self._display_single_remote_decryption_request(
                    status=status, decryption_request=decryption_request)
                root.add_widget(decryption_request_entry)
            scroll.add_widget(root)
            tab_per_status[status].add_widget(scroll)

    @staticmethod
    def sort_list_revelation_request_per_status(list_authenticator_decryption_requests):
        DECRYPTION_REQUEST_STATUSES = ["PENDING", "ACCEPTED", "REJECTED"]  # KEEP IN SYNC with WASERVER
        decryption_requests_per_status = {status: [] for status in DECRYPTION_REQUEST_STATUSES}

        for decryption_request in list_authenticator_decryption_requests:
            decryption_requests_per_status[decryption_request["revelation_request_status"]].append(decryption_request)
        return decryption_requests_per_status

    @safe_catch_unhandled_exception_and_display_popup
    def fetch_and_display_revelation_requests(self):

        self.ids.pending_decryption_request.clear_widgets()
        self.ids.rejected_decryption_request.clear_widgets()
        self.ids.accepted_decryption_request.clear_widgets()

        authenticator_path = self.selected_authenticator_dir

        authenticator_metadata = load_keystore_metadata(authenticator_path)
        keystore_uid = authenticator_metadata["keystore_uid"]

        try:
            list_authenticator_revelation_requests = self.gateway_proxy.list_authenticator_revelation_requests(
                authenticator_keystore_secret=authenticator_metadata["keystore_secret"],
                authenticator_keystore_uid=keystore_uid)

        except KeystoreDoesNotExist:  # FIXME why would this pop out ? Why not just an empty list ???
            # Fixme Because without this popup, we do not understand why the empty screen is empty
            display_info_snackbar(tr._("Authenticator %s does not exist on remote server") % keystore_uid)
            return

        except AuthenticationError:
            display_info_snackbar(tr._("The keystore secret of authenticator is not valid"))
            return

        # FIXME ADD PLACEHOLDER WHEN list_authenticator_revelation_requests is empty


        list_revelation_requests_per_status = self.sort_list_revelation_request_per_status(
            list_authenticator_revelation_requests)

        self.display_remote_decryption_request(list_revelation_requests_per_status=list_revelation_requests_per_status)

    @safe_catch_unhandled_exception_and_display_popup
    def accept_revelation_request(self, passphrase, decryption_request):
        # USE THIS FORM BEFORE :                text=tr._("Confirm removal"), on_release=lambda *args: (
        #                         close_current_dialog(), self.delete_keystores(keystore_uids=keystore_uids))
        authenticator_metadata = load_keystore_metadata(keystore_dir=self.selected_authenticator_dir)
        filesystem_keystore = FilesystemKeystore(self.selected_authenticator_dir)
        trustee_api = TrusteeApi(keystore=filesystem_keystore)
        symkey_decryption_results = []

        # FIXME check passphrase first and report error, instead of leaving "abnormal error" flowing to safe_catch_unhandled_exception_and_display_popup

        for symkey_decryption in decryption_request["symkey_decryption_requests"]:
            decryption_status = SymkeyDecryptionStatus.DECRYPTED
            keychain_uid = symkey_decryption["target_public_authenticator_key"]["keychain_uid"]
            cipher_algo = symkey_decryption["target_public_authenticator_key"]["key_algo"]
            passphrases = [passphrase]
            cipherdict = load_from_json_bytes(symkey_decryption["symkey_decryption_request_data"])
            response_data = b""
            try:

                key_struct_bytes = trustee_api.decrypt_with_private_key(keychain_uid=keychain_uid,
                                                                        cipher_algo=cipher_algo,
                                                                        cipherdict=cipherdict, passphrases=passphrases)
                response_key_algo = decryption_request["revelation_response_key_algo"]
                response_public_key = decryption_request["revelation_response_public_key"]

                public_key = load_asymmetric_key_from_pem_bytestring(key_pem=response_public_key, key_algo=cipher_algo)

                response_data_dict = encrypt_bytestring(
                    plaintext=key_struct_bytes, cipher_algo=response_key_algo, key_dict=dict(key=public_key)
                )
                response_data = dump_to_json_bytes(response_data_dict)

            except KeyDoesNotExist:
                decryption_status = SymkeyDecryptionStatus.PRIVATE_KEY_MISSING

            except KeyLoadingError:
                display_info_snackbar(tr._("Loading of private key failed (wrong passphrase?)"))
                return

            symkey_decryption_result = {
                "symkey_decryption_request_data": symkey_decryption["symkey_decryption_request_data"],
                "symkey_decryption_response_data": response_data,
                "symkey_decryption_status": decryption_status
            }

            symkey_decryption_results.append(symkey_decryption_result)

        revelation_request_uid = decryption_request["revelation_request_uid"]

        self.gateway_proxy.accept_revelation_request(
            authenticator_keystore_secret=authenticator_metadata["keystore_secret"],
            revelation_request_uid=revelation_request_uid,
            symkey_decryption_results=symkey_decryption_results)

        message = tr._("The decryption request was accepted")

        close_current_dialog()
        display_info_snackbar(message)
        self.fetch_and_display_revelation_requests()

    @safe_catch_unhandled_exception_and_display_popup
    def reject_revelation_request(self, decryption_request):
        # USE THIS FORM BEFORE :                text=tr._("Confirm removal"), on_release=lambda *args: (
        #                         close_current_dialog(), self.delete_keystores(keystore_uids=keystore_uids))
        authenticator_metadata = load_keystore_metadata(keystore_dir=self.selected_authenticator_dir)
        revelation_request_uid = decryption_request["revelation_request_uid"]

        self.gateway_proxy.reject_revelation_request(
            authenticator_keystore_secret=authenticator_metadata["keystore_secret"],
            revelation_request_uid=revelation_request_uid)
        message = tr._("The decryption request was rejected")

        close_current_dialog()
        display_info_snackbar(message)
        self.fetch_and_display_revelation_requests()

    def display_help_popup(self):
        help_text = dedent(tr._("""\
         Add this!!!
         """))
        help_text_popup(
            title=tr._("Remote request decryption page"),
            text=help_text, )
