from pathlib import Path
from textwrap import dedent
from typing import Sequence

from jsonrpc_requests import JSONRPCError
from kivy.factory import Factory
from kivy.lang import Builder
from kivy.properties import ObjectProperty, BooleanProperty
from kivymd.app import MDApp
from kivymd.uix.screen import Screen
from wacryptolib.cryptainer import SHARED_SECRET_ALGO_MARKER, get_trustee_id, gather_decryptable_symkeys
from wacryptolib.jsonrpc_client import JsonRpcProxy, status_slugs_response_error_handler
from wacryptolib.keystore import generate_keypair_for_storage, FilesystemKeystore
from wacryptolib.utilities import load_from_json_bytes, generate_uuid0, dump_to_json_file, load_from_json_file
from wacryptolib.exceptions import KeystoreDoesNotExist, KeyDoesNotExist, KeystoreDoesNotExist

from wacomponents.default_settings import INTERNAL_APP_ROOT
from wacomponents.i18n import tr
from wacomponents.screens.base import WAScreenName
from wacomponents.utilities import shorten_uid, format_authenticator_label
from wacomponents.widgets.popups import display_info_toast, dialog_with_close_button, safe_catch_unhandled_exception_and_display_popup

Builder.load_file(str(Path(__file__).parent / 'claimant_revelation_request_creation_form.kv'))

DESCRIPTION_MIN_LENGTH = 10

# FIXME RENAME THIS FILE AND KV FILE to decryption_request_creation_form.py (and later revelation_request_creation_form.py)

class ClaimantRevelationRequestCreationFormScreen(Screen):
    selected_cryptainer_names = ObjectProperty(None, allownone=True)
    filesystem_keystore_pool = ObjectProperty(None)
    trustee_data = ObjectProperty(None, allownone=True)

    def __init__(self, *args, **kwargs):
        self._app = MDApp.get_running_app()
        super().__init__(*args, **kwargs)

    def go_to_previous_screen(self):
        self.manager.current = WAScreenName.cryptainer_decryption_process

    def go_to_management_screen(self):
        self.manager.current = WAScreenName.cryptainer_storage_management

    def _get_cryptainers_with_cryptainer_names(self, cryptainer_names):  # FIXME wrong naming, not "with", returns PAIRS
        cryptainers = []
        for cryptainer_name in cryptainer_names:
            cryptainer = self.filesystem_cryptainer_storage.load_cryptainer_from_storage(cryptainer_name)
            cryptainers.append((cryptainer_name, cryptainer))
        return cryptainers

    def display_claimant_revelation_request_creation_form(self):
        self.ids.authenticator_checklist.clear_widgets()

        # Display summary
        cryptainer_names = [str(cryptainer_name) for cryptainer_name in self.selected_cryptainer_names]

        cryptainer_string_names = "\n\t".join(cryptainer_names)

        _displayed_values = dict(
            containers_selected=cryptainer_string_names,
            gateway_url=self._app.get_wagateway_url()
        )

        revelation_request_summary_text = dedent(tr._("""\
                                            Container(s) selected: 
                                                {containers_selected}
                                            
                                            Gateway url: {gateway_url}                                           
                                        """)).format(**_displayed_values)

        self.ids.revelation_request_summary.text = revelation_request_summary_text

        # Display the list of required authenticators
        for trustee_info, trustee_keypair_identifiers in self.trustee_data:
            keystore_uid = trustee_info["keystore_uid"]
            authenticator_label = format_authenticator_label(authenticator_owner=trustee_info["keystore_owner"],
                                                             keystore_uid=keystore_uid)

            authenticator_entry = Factory.ListItemWithCheckbox(
                text=tr._("Authenticator {authenticator_label}").format(authenticator_label=authenticator_label))
            authenticator_entry.unique_identifier = keystore_uid
            self.ids.authenticator_checklist.add_widget(authenticator_entry)

    def _create_and_return_response_keypair_from_local_factory(self):
        local_keystore = self.filesystem_keystore_pool.get_local_keyfactory()
        response_keychain_uid = generate_uuid0()
        response_key_algo = "RSA_OAEP"
        generate_keypair_for_storage(key_algo=response_key_algo, keystore=local_keystore,
                                     keychain_uid=response_keychain_uid)
        response_public_key = local_keystore.get_public_key(keychain_uid=response_keychain_uid,
                                                            key_algo=response_key_algo)

        return response_keychain_uid, response_key_algo, response_public_key

    def _get_selected_authenticator(self):
        selected_authenticator = []
        for authenticator_entry in self.ids.authenticator_checklist.children:
            if authenticator_entry.ids.check.active:
                selected_authenticator.append(authenticator_entry.unique_identifier)
        return selected_authenticator

    @safe_catch_unhandled_exception_and_display_popup
    def submit_decryption_request(self):

        revelation_requestor_uid = self._app.get_wa_device_uid()

        gateway_proxy = self._app.get_gateway_proxy()

        # Authenticator selected
        authenticator_selected = self._get_selected_authenticator()
        if not authenticator_selected:
            msg = tr._("Please select authenticators")
            display_info_toast(msg)
            return

        # Description not empty (description.strip must have at least 10 characters)
        request_description = self.ids.request_description.text.strip()
        if len(request_description) < DESCRIPTION_MIN_LENGTH:
            display_info_toast(tr._("Description must be at least %s characters long.") % DESCRIPTION_MIN_LENGTH)
            return

        # Symkeys decryptable per trustee for containers selected
        cryptainers_with_names = self._get_cryptainers_with_cryptainer_names(self.selected_cryptainer_names)

        decryptable_symkeys_per_trustee = gather_decryptable_symkeys(cryptainers_with_names)

        # Response keypair used to encrypt the decrypted symkey/shard
        response_keychain_uid, response_key_algo, response_public_key = self._create_and_return_response_keypair_from_local_factory()

        successful_request_count = 0
        error = []
        # message = ""
        for trustee_id, decryptable_data in decryptable_symkeys_per_trustee.items():
            trustee_data, symkey_decryption_requests = decryptable_data
            if trustee_data["keystore_uid"] in authenticator_selected:
                try:
                    gateway_proxy.submit_revelation_request(authenticator_keystore_uid=trustee_data["keystore_uid"],
                                                            revelation_requestor_uid=revelation_requestor_uid,
                                                            revelation_request_description=request_description,
                                                            revelation_response_public_key=response_public_key,
                                                            revelation_response_keychain_uid=response_keychain_uid,
                                                            revelation_response_key_algo=response_key_algo,
                                                            symkey_decryption_requests=symkey_decryption_requests)

                    # stocker les infos utiles dans operation_report
                    successful_request_count += 1

                except KeystoreDoesNotExist:
                    message = tr._(
                        "Authenticator %s does not exist in sql storage" % shorten_uid(trustee_data["keystore_uid"]))
                    error.append(message)

                except KeyDoesNotExist as exc:
                    message = tr._("Public key needed does not exist in key storage in %s authenticator" % shorten_uid(
                        trustee_data["keystore_uid"]))
                    error.append(message)

        error_report = ",\n    - ".join(error)

        _displayed_values = dict(
            successful_request_count=successful_request_count,
            len_authenticator_selected=len(authenticator_selected),
            error_report=error_report
        )

        operation_report_text = dedent(tr._("""\
                        Successful requests: {successful_request_count} sur {len_authenticator_selected}
                                                """)).format(**_displayed_values)

        error_report_text = dedent(tr._("""\
        
                                                Error Report: 
                                                    - {error_report}                                           
                                                        """)).format(**_displayed_values)

        if successful_request_count != len(authenticator_selected):
            operation_report_text += error_report_text

        dialog_with_close_button(
            close_btn_label=tr._("Close"),
            title=tr._("Operation Report"),
            text=operation_report_text,
            close_btn_callback=self.go_to_management_screen()
        )
