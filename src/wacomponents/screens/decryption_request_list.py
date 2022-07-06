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

from wacomponents.widgets.layout_components import GrowingAccordion
from wacomponents.i18n import tr
from wacomponents.utilities import shorten_uid
from wacomponents.widgets.popups import dialog_with_close_button

Builder.load_file(str(Path(__file__).parent / 'decryption_request_list.kv'))


# FIXME RENAME THIS FILE AND KV FILE to decryption_request_visualization.py (and later revelation_request_visualization.py)

class DecryptionRequestListScreen(Screen):

    def __init__(self, *args, **kwargs):
        self._app = MDApp.get_running_app()
        self.gateway_proxy = self._app.get_gateway_proxy()
        super().__init__(*args, **kwargs)

    def go_to_previous_screen(self):
        self.manager.current = "CryptainerManagement"


    @staticmethod
    def _list_decryption_request_reformatted(list_decryption_request):  # FIXME both have wrong named, and restructured better than reformatted (which means strings)
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
            list_decryption_requests = self.gateway_proxy.list_requestor_revelation_requests(revelation_requestor_uid)

        except(JSONRPCError, OSError):
            display_layout = Factory.WABigInformationBox()
            display_layout.ids.inner_label.text = tr._("Error calling method, check the server url")  # FIXME simplify this
            self.ids.list_decryption_request_scrollview.add_widget(display_layout)
            return

        except ExistenceError:
            display_layout = Factory.WABigInformationBox()
            display_layout.ids.inner_label.text = tr._("No decryption request")  # FIXME simplify this
            self.ids.list_decryption_request_scrollview.add_widget(display_layout)
            return

        decryption_requests_per_cryptainer = self._list_decryption_request_reformatted(list_decryption_requests)

        display_layout = GrowingAccordion(orientation='vertical', size_hint=(1, None))

        for decryption_request_per_cryptainer in decryption_requests_per_cryptainer.items():

            container_item = Factory.ContainerItem(title='Cryptainer: %s ' % decryption_request_per_cryptainer[0])

            for decryption_request in decryption_request_per_cryptainer[1]:
                _displayed_values = dict(
                    revelation_request_uid=decryption_request["revelation_request_uid"],
                    revelation_request_description=decryption_request["revelation_request_description"],
                    target_public_authenticator=decryption_request["target_public_authenticator"]["keystore_owner"],
                    revelation_request_status=decryption_request["revelation_request_status"],
                    revelation_response_keychain_uid=decryption_request["revelation_response_keychain_uid"],
                    revelation_response_key_algo=decryption_request["revelation_response_key_algo"],
                    symkey_decryption_status=decryption_request["symkey_decryption_request"]["symkey_decryption_status"],
                    key_algo=decryption_request["symkey_decryption_request"]["target_public_authenticator_key"]["key_algo"],
                    keychain_uid=decryption_request["symkey_decryption_request"]["target_public_authenticator_key"]["keychain_uid"],
                )

                # FIXME retranslate all these text blocks, using update_i18n.sh
                decryption_request_summary_text = dedent(tr._("""\
                                                           Revelation request uid: {revelation_request_uid}
                                                           Description: {revelation_request_description}
                                                           Authenticator: {target_public_authenticator}, {keychain_uid}({key_algo})
                                                           Request status: {revelation_request_status}
                                                           Response key: {revelation_response_keychain_uid}({revelation_response_key_algo})
                                                           Symkey Decryption status: {symkey_decryption_status}
                                                       """)).format(**_displayed_values)

                decryption_request_entry = Factory.WAIconListItemEntry(text="Revelation request uid: %s, Status: %s" % (
                    shorten_uid(decryption_request["revelation_request_uid"]), decryption_request["revelation_request_status"]))

                def information_callback(widget, decryption_request_info=decryption_request_summary_text):
                    self.show_decryption_request_info(decryption_request_info=decryption_request_info)

                information_icon = decryption_request_entry.ids.information_icon
                information_icon.bind(on_press=information_callback)

                container_item.decryption_requests_list.add_widget(decryption_request_entry)

            display_layout.add_widget(container_item)
        self.ids.list_decryption_request_scrollview.add_widget(display_layout)

    def show_decryption_request_info(self, decryption_request_info):
        dialog_with_close_button(
            close_btn_label=tr._("Close"),
            title=tr._("Revelation Request Summary"),
            text=decryption_request_info,
        )
