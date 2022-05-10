from pathlib import Path
from textwrap import dedent

from jsonrpc_requests import JSONRPCError
from kivy.lang import Builder
from kivy.properties import ObjectProperty, BooleanProperty, StringProperty
from kivy.uix.accordion import Accordion

from kivymd.app import MDApp
from kivy.factory import Factory
from kivymd.uix.button import MDFlatButton
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.screen import Screen
from kivymd.uix.tab import MDTabsBase
from wacryptolib.cipher import encrypt_bytestring
from wacryptolib.exceptions import ExistenceError, KeyLoadingError, KeyDoesNotExist, DecryptionError
from wacryptolib.jsonrpc_client import JsonRpcProxy, status_slugs_response_error_handler
from wacryptolib.keygen import load_asymmetric_key_from_pem_bytestring
from wacryptolib.keystore import load_keystore_metadata, FilesystemKeystore
from wacryptolib.trustee import TrusteeApi
from wacryptolib.utilities import load_from_json_bytes

from wacomponents.i18n import tr
from wacomponents.screens.decryption_request_list import GrowingAccordion
from wacomponents.utilities import shorten_uid
from wacomponents.widgets.popups import dialog_with_close_button, close_current_dialog, display_info_snackbar, \
    help_text_popup

Builder.load_file(str(Path(__file__).parent / 'authenticator_remote_decryption_request.kv'))


class Tab(MDFloatLayout, MDTabsBase):
    """Class implementing content for a tab."""


class DecryptionStatus():
    DECRYPTED = 'DECRYPTED'
    PRIVATE_KEY_MISSING = 'PRIVATE KEY MISSING'
    CORRUPTED = 'CORRUPTED'
    MISMATCH = 'METADATA MISMATCH'
    PENDING = 'PENDING'


class RemoteDecryptionRequestScreen(Screen):
    index = 0
    selected_authenticator_dir = ObjectProperty(None, allownone=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._app = MDApp.get_running_app()

    def go_to_home_screen(self):  # Fixme deduplicate and push to App!
        self.manager.current = "authenticator_selector_screen"

    def _get_gateway_proxy(self):
        jsonrpc_url = self._app.get_wagateway_url()
        gateway_proxy = JsonRpcProxy(
            url=jsonrpc_url, response_error_handler=status_slugs_response_error_handler
        )
        return gateway_proxy

    def _display_single_remote_decryption_request(self, status, decryption_request):

        decryptionRequestEntry = Factory.DecryptionRequestEntry()

        decryptionRequestEntry.title = tr._("Request : {decryption_request_uid}").format(
            decryption_request_uid=decryption_request["decryption_request_uid"])

        _displayed_values = dict(
            public_authenticator=decryption_request["public_authenticator"]["keystore_owner"],
            requester_uid=decryption_request["requester_uid"],
            description=decryption_request["description"],
            response_keychain_uid=shorten_uid(decryption_request["response_keychain_uid"]),
            response_key_algo=decryption_request["response_key_algo"]
        )

        decryption_request_summary_text = dedent(tr._("""\
                                    Authenticator: {public_authenticator}
                                    Requester ID: {requester_uid}
                                    Description: {description}
                                    Response public key: {response_keychain_uid}({response_key_algo})
                                """)).format(**_displayed_values)

        decryptionRequestEntry.decryption_request_summary.text = decryption_request_summary_text

        for index, symkey_decryption in enumerate(decryption_request['symkeys_decryption'], start=1):
            symkey_decryption_label = tr._("Container N° {key_index}: {Container_uid} "). \
                format(key_index=index, Container_uid=symkey_decryption["cryptainer_uid"])

            symkey_decryption_item = Factory.WAIconListItemEntry(text=symkey_decryption_label)  # FIXME RENAME THIS

            def information_callback(widget, symkey_decryption=symkey_decryption):
                self.show_symkey_decryption_details(symkey_decryption=symkey_decryption)

            information_icon = symkey_decryption_item.ids.information_icon
            information_icon.bind(on_press=information_callback)

            decryptionRequestEntry.symkeys_decryption.add_widget(symkey_decryption_item)

        if status == DecryptionStatus.PENDING:
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
            key_algo=symkey_decryption["authenticator_public_key"]["key_algo"],
            keychain_uid=symkey_decryption["authenticator_public_key"]["keychain_uid"],
            cryptainer_uid=symkey_decryption["cryptainer_uid"],
            cryptainer_metadata=symkey_decryption["cryptainer_metadata"],
            request_data=symkey_decryption["request_data"],
            decryption_status=symkey_decryption["decryption_status"]
        )

        symkey_decryption_info_text = dedent(tr._("""\
                                   Cryptainer uid: {cryptainer_uid}
                                   Cryptainer metadata: {cryptainer_metadata}
                                   Key needeed: {keychain_uid}({key_algo})
                                   Decryption status: {decryption_status}
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
                MDFlatButton(text=tr._("Accept"), on_release=lambda *args: self.accept_decryption_request(
                    passphrase=dialog.content_cls.ids.passphrase.text, decryption_request=decryption_request))],
        )

    def open_dialog_reject_request(self, decryption_request):
        dialog_with_close_button(
            close_btn_label=tr._("Cancel"),
            title=tr._("Do you want to reject this request?"),
            type="custom",
            buttons=[
                MDFlatButton(text=tr._("Reject"), on_release=lambda *args: self.reject_decryption_request(
                    decryption_request=decryption_request))],
        )

    def display_remote_decryption_request(self, list_decryption_requests_per_status):  # TODO change name function
        # TODO add list_decryption_request to parameter of this function

        tab_per_status = dict(PENDING=self.ids.pending_decryption_request,
                              REJECTED=self.ids.rejected_decryption_request,
                              ACCEPTED=self.ids.accepted_decryption_request)

        for status, decryption_requests in list_decryption_requests_per_status.items():

            if not decryption_requests:
                display_layout = Factory.WABigInformationBox()
                display_layout.ids.inner_label.text = tr._("Aucune demande de déchiffrement")
                tab_per_status[status].add_widget(display_layout)
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
    def sort_list_decryption_request_per_status(list_authenticator_decryption_requests):
        DECRYPTION_REQUEST_STATUSES = ["PENDING", "ACCEPTED", "REJECTED"]  # KEEP IN SYNC with WASERVER
        decryption_requests_per_status = {
            DECRYPTION_REQUEST_STATUSES[0]: [],
            DECRYPTION_REQUEST_STATUSES[1]: [],
            DECRYPTION_REQUEST_STATUSES[2]: []
        }
        for decryption_request in list_authenticator_decryption_requests:
            decryption_requests_per_status[decryption_request["request_status"]].append(decryption_request)
        return decryption_requests_per_status

    def fetch_and_display_decryption_requests(self):

        self.ids.pending_decryption_request.clear_widgets()
        self.ids.rejected_decryption_request.clear_widgets()
        self.ids.accepted_decryption_request.clear_widgets()

        gateway_proxy = self._get_gateway_proxy()

        authenticator_path = self.selected_authenticator_dir

        authenticator_metadata = load_keystore_metadata(authenticator_path)
        keystore_uid = authenticator_metadata["keystore_uid"]

        try:
            list_authenticator_decryption_requests = gateway_proxy.list_authenticator_decryption_requests(keystore_uid)

        except(JSONRPCError, OSError):
            display_info_snackbar(tr._("Error calling method, check the server url"))
            return

        except ExistenceError:
            display_info_snackbar(tr._("No decryption request"))
            return

        list_decryption_requests_per_status = self.sort_list_decryption_request_per_status(
            list_authenticator_decryption_requests)

        self.display_remote_decryption_request(list_decryption_requests_per_status=list_decryption_requests_per_status)

    def accept_decryption_request(self, passphrase, decryption_request):

        filesystem_keystore = FilesystemKeystore(self.selected_authenticator_dir)
        trustee_api = TrusteeApi(keystore=filesystem_keystore)
        symkey_decryption_results = []

        for symkey_decryption in decryption_request["symkeys_decryption"]:
            decryption_status = DecryptionStatus.DECRYPTED
            keychain_uid = symkey_decryption["authenticator_public_key"]["keychain_uid"]
            cipher_algo = symkey_decryption["authenticator_public_key"]["key_algo"]
            passphrases = [passphrase]
            cipherdict = load_from_json_bytes(symkey_decryption["request_data"])
            response_data = b""
            try:

                key_struct_bytes = trustee_api.decrypt_with_private_key(keychain_uid=keychain_uid,
                                                                        cipher_algo=cipher_algo,
                                                                        cipherdict=cipherdict, passphrases=passphrases)
                response_key_algo = decryption_request["response_key_algo"]
                response_public_key = decryption_request["response_public_key"]

                public_key = load_asymmetric_key_from_pem_bytestring(key_pem=response_public_key, key_algo=cipher_algo)

                response_data = encrypt_bytestring(
                    plaintext=key_struct_bytes, cipher_algo=response_key_algo, key_dict=dict(key=public_key)
                )
            except KeyDoesNotExist:
                decryption_status = DecryptionStatus.PRIVATE_KEY_MISSING

            except KeyLoadingError:
                display_info_snackbar(tr._("Passphrase doesn't match any relevant private key"))
                return

            symkey_decryption_result = {
                "request_data": symkey_decryption["request_data"],
                "response_data": response_data,
                "decryption_status": decryption_status
            }

            symkey_decryption_results.append(symkey_decryption_result)

        gateway_proxy = self._get_gateway_proxy()
        decryption_request_uid = decryption_request["decryption_request_uid"]
        message = tr._("The decryption request was accepted")

        try:
            gateway_proxy.accept_decryption_request(decryption_request_uid=decryption_request_uid,
                                                    symkey_decryption_results=symkey_decryption_results)
        except (JSONRPCError, OSError):
            message = tr._("Error calling method, check the server url")

        close_current_dialog()
        display_info_snackbar(message)
        self.fetch_and_display_decryption_requests()

    def reject_decryption_request(self, decryption_request):
        gateway_proxy = self._get_gateway_proxy()
        decryption_request_uid = decryption_request["decryption_request_uid"]
        message = tr._("The decryption request was rejected")
        try:
            gateway_proxy.reject_decryption_request(decryption_request_uid=decryption_request_uid)
        except (JSONRPCError, OSError):
            message = tr._("Error calling method, check the server url")
        close_current_dialog()
        display_info_snackbar(message)
        self.fetch_and_display_decryption_requests()

    def display_help_popup(self):
        help_text = dedent(tr._("""\
         Add this!!!
         """))
        help_text_popup(
            title=tr._("Remote request decryption page"),
            text=help_text, )
