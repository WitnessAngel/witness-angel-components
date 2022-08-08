from pathlib import Path
from textwrap import dedent

from jsonrpc_requests import JSONRPCError
from kivy.factory import Factory
from kivy.lang import Builder
from kivy.uix.accordion import Accordion, AccordionItem
from kivymd.app import MDApp
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.list import MDList
from kivymd.uix.screen import Screen
from wacryptolib.jsonrpc_client import JsonRpcProxy, status_slugs_response_error_handler
from wacryptolib.exceptions import ExistenceError

from wacomponents.widgets.layout_components import GrowingAccordion, build_fallback_information_box
from wacomponents.i18n import tr
from wacomponents.utilities import shorten_uid, format_revelation_request_label, format_authenticator_label, \
    format_keypair_label
from wacomponents.widgets.popups import dialog_with_close_button, display_info_snackbar

Builder.load_file(str(Path(__file__).parent / 'claimant_revelation_request_management.kv'))


# FIXME RENAME THIS FILE AND KV FILE to decryption_request_visualization.py (and later revelation_request_visualization.py)

class ClaimantRevelationRequestManagementScreen(Screen):

    def __init__(self, *args, **kwargs):
        self._app = MDApp.get_running_app()
        self.gateway_proxy = self._app.get_gateway_proxy()
        super().__init__(*args, **kwargs)

    def go_to_previous_screen(self):
        self.manager.current = "CryptainerManagement"

    @staticmethod
    def _list_decryption_request_reformatted(
            list_decryption_request):  # FIXME both have wrong named, and restructured better than reformatted (which means strings)
        decryption_request_per_cryptainer = {}

        for decryption_request in list_decryption_request:

            decryption_request_per_symkey = {key: value for key, value in decryption_request.items() if
                                             key != 'symkey_decryption_requests'}

            for symkey_decryption_request in decryption_request["symkey_decryption_requests"]:
                decryption_request_per_symkey["symkey_decryption_request"] = symkey_decryption_request

                cryptainer_uid = symkey_decryption_request["cryptainer_uid"]
                _decryption_request_per_cryptainer = decryption_request_per_cryptainer.setdefault(cryptainer_uid, [])
                _decryption_request_per_cryptainer.append(decryption_request_per_symkey)

        return decryption_request_per_cryptainer

    def display_decryption_request_list(self):
        self.ids.list_decryption_request_scrollview.clear_widgets()

        revelation_requestor_uid = self._app.get_wa_device_uid()

        try:
            list_decryption_requests = self.gateway_proxy.list_requestor_revelation_requests(
                revelation_requestor_uid=revelation_requestor_uid)  # FIXME RENAME list_decryption_requests

        except(JSONRPCError, OSError):
            display_info_snackbar(tr._("Network error, please check the gateway url"))
            list_decryption_requests = []

        if not list_decryption_requests:  # FIXME RENAME ALL decryption requests!!!!
            fallback_info_box = build_fallback_information_box(tr._("No revelation requests found"))
            self.ids.list_decryption_request_scrollview.add_widget(fallback_info_box)
            return

        decryption_requests_per_cryptainer = self._list_decryption_request_reformatted(list_decryption_requests)

        display_layout = GrowingAccordion(orientation='vertical', size_hint=(1, None))

        for decryption_request_per_cryptainer in decryption_requests_per_cryptainer.items():

            container_item = Factory.ContainerItem(title='Cryptainer: %s ' % decryption_request_per_cryptainer[0])

            for revelation_request in decryption_request_per_cryptainer[1]:
                print(revelation_request)
                revelation_request_label = format_revelation_request_label(
                    revelation_request_uid=revelation_request["revelation_request_uid"],
                    revelation_request_creation_datetime=revelation_request["created_at"],
                    revelation_request_status=revelation_request["revelation_request_status"])

                target_public_authenticator_label = format_authenticator_label(
                    authenticator_owner=revelation_request["target_public_authenticator"]["keystore_owner"],
                    keystore_uid=revelation_request["target_public_authenticator"]["keystore_uid"])

                authenticator_key_algo = revelation_request["symkey_decryption_request"]["target_public_authenticator_key"]["key_algo"]
                authenticator_keychain_uid = revelation_request["symkey_decryption_request"]["target_public_authenticator_key"]["keychain_uid"]

                authenticator_key_label = format_keypair_label(keychain_uid=authenticator_keychain_uid,
                                                               key_algo=authenticator_key_algo)

                response_key_label = format_keypair_label(
                    keychain_uid=revelation_request["revelation_response_keychain_uid"],
                    key_algo=revelation_request["revelation_response_key_algo"])

                _displayed_values = dict(
                    revelation_request_label=revelation_request_label,
                    revelation_request_description=revelation_request["revelation_request_description"],
                    target_public_authenticator_label=target_public_authenticator_label,
                    response_key_label=response_key_label,
                    symkey_decryption_status=revelation_request["symkey_decryption_request"][
                        "symkey_decryption_status"],
                    authenticator_key_label=authenticator_key_label,
                )

                # FIXME retranslate all these text blocks, using update_i18n.sh
                revelation_request_summary_text = dedent(tr._("""\
                                    Description: {revelation_request_description}
                                    Authenticator: {target_public_authenticator_label}
                                    Authenticator encryption key: {authenticator_key_label}
                                    Response key: {response_key_label}
                                    Symkey Decryption status: {symkey_decryption_status}
                                                                       """)).format(**_displayed_values)

                decryption_request_entry = Factory.WAIconListItemEntry(text=revelation_request_label)

                def information_callback(widget, revelation_request_info=revelation_request_summary_text):
                    self.show_revelation_request_info(revelation_request_info=revelation_request_info)

                information_icon = decryption_request_entry.ids.information_icon
                information_icon.bind(on_press=information_callback)

                container_item.decryption_requests_list.add_widget(decryption_request_entry)

            display_layout.add_widget(container_item)
        self.ids.list_decryption_request_scrollview.add_widget(display_layout)

    def show_revelation_request_info(self, revelation_request_info):
        dialog_with_close_button(
            close_btn_label=tr._("Close"),
            title=tr._("Revelation Request Summary"),
            text=revelation_request_info,
        )
