from pathlib import Path

from jsonrpc_requests import JSONRPCError
from kivy.factory import Factory
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.screen import Screen

from wacomponents.screens.base import WAScreenName
from wacomponents.widgets.layout_components import GrowingAccordion, build_fallback_information_box
from wacomponents.i18n import tr
from wacomponents.utilities import format_revelation_request_label, format_authenticator_label, \
    format_keypair_label, COLON, LINEBREAK, format_cryptainer_label
from wacomponents.widgets.popups import dialog_with_close_button, display_info_snackbar

Builder.load_file(str(Path(__file__).parent / 'claimant_revelation_request_management.kv'))


# FIXME RENAME THIS FILE AND KV FILE to decryption_request_visualization.py (and later revelation_request_visualization.py)

class ClaimantRevelationRequestManagementScreen(Screen):

    def __init__(self, *args, **kwargs):
        self._app = MDApp.get_running_app()
        super().__init__(*args, **kwargs)

    def go_to_previous_screen(self):
        self.manager.current = WAScreenName.cryptainer_storage_management

    @staticmethod
    def _list_revelation_request_reformatted(
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

    def list_requestor_revelation_requests(self):
        revelation_requestor_uid = self._app.get_wa_device_uid()
        gateway_proxy = self._app.get_gateway_proxy()
        try:
            requestor_revelation_requests = gateway_proxy.list_requestor_revelation_requests(
                revelation_requestor_uid=revelation_requestor_uid)  # FIXME RENAME list_decryption_requests
        except(JSONRPCError, OSError):
            requestor_revelation_requests = None

        return requestor_revelation_requests


    def display_decryption_request_list(self):
        self.ids.list_decryption_request_scrollview.clear_widgets()

        def resultat_callable(requestor_revelation_requests, *args, **kwargs):  # FIXME CHANGE THIS NAME
            if requestor_revelation_requests is None:
                display_info_snackbar(tr._("Network error, please check the gateway url"))
                return

            if requestor_revelation_requests == []:  # FIXME RENAME ALL decryption requests!!!!
                fallback_info_box = build_fallback_information_box(tr._("No revelation requests found"))
                self.ids.list_decryption_request_scrollview.add_widget(fallback_info_box)
                return

            revelation_requests_per_cryptainer = self._list_revelation_request_reformatted(requestor_revelation_requests)

            display_layout = GrowingAccordion(orientation='vertical', size_hint=(1, None))

            for revelation_request_per_cryptainer in revelation_requests_per_cryptainer.items():
                print(revelation_request_per_cryptainer)

                cryptainer_name = revelation_request_per_cryptainer[1][0]["symkey_decryption_request"]["cryptainer_name"]
                cryptainer_uid = revelation_request_per_cryptainer[1][0]["symkey_decryption_request"]["cryptainer_uid"]
                assert cryptainer_uid == revelation_request_per_cryptainer[0]
                cryptainer_label = format_cryptainer_label(cryptainer_name=cryptainer_name,
                                                           cryptainer_uid=cryptainer_uid)

                container_item = Factory.ContainerItem(title=tr._("Container") + " " + cryptainer_label)

                for revelation_request in revelation_request_per_cryptainer[1]:

                    revelation_request_label1 = format_revelation_request_label(
                        revelation_request_uid=revelation_request["revelation_request_uid"],
                        revelation_request_creation_datetime=revelation_request["created_at"])

                    revelation_request_label2 = tr._("Status") + COLON() + revelation_request["revelation_request_status"]

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

                    _displayed_values = dict(  # FIXME remove that
                        revelation_request_description=revelation_request["revelation_request_description"],
                        target_public_authenticator_label=target_public_authenticator_label,
                        response_key_label=response_key_label,
                        symkey_decryption_status=revelation_request["symkey_decryption_request"][
                            "symkey_decryption_status"],
                        authenticator_key_label=authenticator_key_label,
                    )

                    revelation_request_summary_text = tr._("Description") + COLON() + _displayed_values["revelation_request_description"] + 2*LINEBREAK + \
                                                      tr._("Authenticator") + COLON() + _displayed_values["target_public_authenticator_label"] + LINEBREAK + \
                                                      tr._("Authenticator key") + COLON() + _displayed_values["authenticator_key_label"] + LINEBREAK + \
                                                      tr._("Local response key") + COLON() + _displayed_values["response_key_label"] + 2*LINEBREAK + \
                                                      tr._("Symkey Decryption status") + COLON() + _displayed_values["symkey_decryption_status"]

                    revelation_request_entry = Factory.WAIconListItemEntry(
                        text=revelation_request_label1, secondary_text=revelation_request_label2)

                    def information_callback(widget, revelation_request_info=revelation_request_summary_text):
                        # We MUST use this "revelation_request_info" parameter to freeze the "variable revelation_request_summary_text"
                        self.show_revelation_request_info(revelation_request_info=revelation_request_info)

                    information_icon = revelation_request_entry.ids.information_icon
                    information_icon.bind(on_press=information_callback)

                    container_item.revelation_requests_list.add_widget(revelation_request_entry)

                display_layout.add_widget(container_item)
            self.ids.list_decryption_request_scrollview.add_widget(display_layout)

        self._app._offload_task_with_spinner(self.list_requestor_revelation_requests, resultat_callable)

    def show_revelation_request_info(self, revelation_request_info):
        dialog_with_close_button(
            close_btn_label=tr._("Close"),
            title=tr._("Revelation request summary"),
            text=revelation_request_info,
        )
