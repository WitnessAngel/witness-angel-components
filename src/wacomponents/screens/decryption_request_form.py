from pathlib import Path
from textwrap import dedent
from typing import Sequence

from jsonrpc_requests import JSONRPCError
from kivy.factory import Factory
from kivy.lang import Builder
from kivy.properties import ObjectProperty, BooleanProperty
from kivymd.app import MDApp
from kivymd.uix.screen import Screen
from wacryptolib.cryptainer import SHARED_SECRET_ALGO_MARKER, _get_trustee_id
from wacryptolib.jsonrpc_client import JsonRpcProxy, status_slugs_response_error_handler
from wacryptolib.keystore import generate_keypair_for_storage
from wacryptolib.utilities import load_from_json_bytes, generate_uuid0
from wacryptolib.exceptions import KeystoreDoesNotExist, KeyDoesNotExist

from wacomponents.i18n import tr
from wacomponents.widgets.popups import display_info_toast, dialog_with_close_button

Builder.load_file(str(Path(__file__).parent / 'decryption_request_form.kv'))

DESCRIPTION_MIN_LENGTH = 10


class DecryptionRequestFormScreen(Screen):
    selected_cryptainer_names = ObjectProperty(None, allownone=True)
    filesystem_keystore_pool = ObjectProperty(None)
    trustee_data = ObjectProperty(None, allownone=True)
    requester_uid = generate_uuid0()

    def __init__(self, *args, **kwargs):
        self._app = MDApp.get_running_app()
        super().__init__(*args, **kwargs)

    def go_to_previous_screen(self):
        self.manager.current = "CryptainerDecryption"

    def _get_gateway_proxy(self):
        jsonrpc_url = self._app.get_wagateway_url()
        gateway_proxy = JsonRpcProxy(
            url=jsonrpc_url, response_error_handler=status_slugs_response_error_handler
        )
        return gateway_proxy

    def _get_cryptainers_with_cryptainer_names(self, cryptainer_names):
        cryptainers = []
        for cryptainer_name in cryptainer_names:
            cryptainer = self.filesystem_cryptainer_storage.load_cryptainer_from_storage(cryptainer_name)
            cryptainers.append(cryptainer)
        return cryptainers

    def display_decryption_request_form(self):
        self.ids.authenticator_checklist.clear_widgets()

        # Display summary
        cryptainers_name = ""

        for cryptainer_name in self.selected_cryptainer_names:
            cryptainers_name = cryptainers_name + "\n\t" + str(cryptainer_name)

        _displayed_values = dict(
            containers_selected=cryptainers_name,
            gateway_url=self._app.get_wagateway_url()
        )

        decryption_request_summary_text = dedent(tr._("""\
                                            Container(s) selected: {containers_selected}
                                            Gateway url: {gateway_url}                                           
                                        """)).format(**_displayed_values)

        self.ids.decryption_request_summary.text = decryption_request_summary_text

        # Display the list of required authenticators
        for trustee_info, trustee_keypair_identifiers in self.trustee_data:
            keystore_uid = trustee_info["keystore_uid"]
            authenticator_entry = Factory.ListItemWithCheckbox(
                text=tr._("Authenticator: {keystore_uid}").format(keystore_uid=keystore_uid))
            authenticator_entry.unique_identifier = keystore_uid
            self.ids.authenticator_checklist.add_widget(authenticator_entry)

    @staticmethod
    def gather_decryptable_symkeys(cryptainers: Sequence) -> dict:

        decryptable_symkeys_per_trustee = {}

        def _add_decryptable_symkeys_for_trustee(key_cipher_trustee, shard_ciphertext, keychain_uid_encryption,
                                                 key_algo_encryption, cryptainer_uid, cryptainer_metadata):

            trustee_id = _get_trustee_id(trustee_conf=key_cipher_trustee)
            symkeys_data_to_decrypt = {
                "cryptainer_uid": cryptainer_uid,
                "cryptainer_metadata": cryptainer_metadata,
                "symkey_ciphertext": shard_ciphertext,
                "keychain_uid": keychain_uid_encryption,
                "key_algo": key_algo_encryption
            }
            _trustee_data, _decryptable_symkeys = decryptable_symkeys_per_trustee.setdefault(trustee_id,
                                                                                             (key_cipher_trustee, []))
            _decryptable_symkeys.append(symkeys_data_to_decrypt)

        def _gather_decryptable_symkeys(key_cipher_layers: list, shard_ciphertexts, cryptainer_uid,
                                        cryptainer_metadata):

            last_key_cipher_layer = key_cipher_layers[-1]

            if last_key_cipher_layer["key_cipher_algo"] == SHARED_SECRET_ALGO_MARKER:
                key_shared_secret_shards = last_key_cipher_layer["key_shared_secret_shards"]

                for shard_ciphertext, trustee in zip(shard_ciphertexts, key_shared_secret_shards):
                    _gather_decryptable_symkeys(trustee["key_cipher_layers"], shard_ciphertext, cryptainer_uid,
                                                cryptainer_metadata)
            else:

                keychain_uid_encryption = last_key_cipher_layer.get("keychain_uid") or keychain_uid
                key_algo_encryption = last_key_cipher_layer["key_cipher_algo"]
                key_cipher_trustee = last_key_cipher_layer["key_cipher_trustee"]
                shard_ciphertext = shard_ciphertexts

                _add_decryptable_symkeys_for_trustee(key_cipher_trustee, shard_ciphertext, keychain_uid_encryption,
                                                     key_algo_encryption,
                                                     cryptainer_uid, cryptainer_metadata)

        for cryptainer in cryptainers:
            keychain_uid = cryptainer["keychain_uid"]
            cryptainer_uid = cryptainer["cryptainer_uid"]
            cryptainer_metadata = cryptainer["cryptainer_metadata"]

            for payload_cipher_layer in cryptainer["payload_cipher_layers"]:
                key_ciphertext_shards = load_from_json_bytes(payload_cipher_layer.get("key_ciphertext"))
                shard_ciphertexts = key_ciphertext_shards["shard_ciphertexts"]

                _gather_decryptable_symkeys(payload_cipher_layer["key_cipher_layers"], shard_ciphertexts,
                                            cryptainer_uid,
                                            cryptainer_metadata)

        return decryptable_symkeys_per_trustee

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

    def submit_decryption_request(self):

        gateway_proxy = self._get_gateway_proxy()

        # Authenticator selected
        authenticator_selected = self._get_selected_authenticator()
        if not authenticator_selected:
            msg = tr._("Please select authenticators")
            display_info_toast(msg)
            return

        # Description no empty(description.strip doit avoir au moins 10 caractères)
        description = self.ids.description.text.strip()
        if len(description) < DESCRIPTION_MIN_LENGTH:
            msg = tr._("Description must be at least %s characters long.") % DESCRIPTION_MIN_LENGTH
            display_info_toast(msg)
            return

        # Symkeys decyptable per trustee for containers selected
        cryptainers = self._get_cryptainers_with_cryptainer_names(self.selected_cryptainer_names)
        decryptable_symkeys_per_trustee = self.gather_decryptable_symkeys(cryptainers)

        # Response keypair utilisé pour chiffrer la reponse
        response_keychain_uid, response_key_algo, response_public_key = self._create_and_return_response_keypair_from_local_factory()

        successful_request = 0
        error_report = []
        for trustee_id, decryptable_data in decryptable_symkeys_per_trustee.items():
            trustee_data, symkeys_data_to_decrypt = decryptable_data
            if trustee_data["keystore_uid"] in authenticator_selected:
                # faire try except
                try:
                    gateway_proxy.submit_decryption_request(keystore_uid=trustee_data["keystore_uid"],
                                                            requester_uid=self.requester_uid,
                                                            description=description,
                                                            response_public_key=response_public_key,
                                                            response_keychain_uid=response_keychain_uid,
                                                            response_key_algo=response_key_algo,
                                                            symkeys_data_to_decrypt=symkeys_data_to_decrypt)
                    # stocker les infos utiles dans operation_report
                    successful_request += 1

                except (JSONRPCError, OSError):
                    message = tr._("Error calling method, check the server url")
                    error_report.append(message)

                except (KeystoreDoesNotExist, KeyDoesNotExist) as exc:
                    error_report.append((trustee_data["keystore_uid"], exc))

        _displayed_values = dict(
            successful_request=successful_request,
            len_authenticator_selected=len(authenticator_selected),
            errror_report=error_report
        )

        operation_report_text = dedent(tr._("""\
                                                    Successful request(s): {successful_request} sur {len_authenticator_selected}
                                                    Error(s) Report: {errror_report}                                           
                                                """)).format(**_displayed_values)

        dialog_with_close_button(
            close_btn_label=tr._("Close"),
            title=tr._("Operation Report"),
            text=operation_report_text,
            close_btn_callback=self.go_to_previous_screen()
        )

        # afficher POPUP avec le rapport (X réussis, et erreurs : <liste à bulle>)
        # quand on ferme popup, retourner sur page précédente
