from pathlib import Path
from textwrap import dedent
from typing import Sequence

from kivy.factory import Factory
from kivy.lang import Builder
from kivy.properties import ObjectProperty, BooleanProperty
from kivymd.app import MDApp
from kivymd.uix.screen import Screen
from wacryptolib.cryptainer import SHARED_SECRET_ALGO_MARKER, _get_trustee_id
from wacryptolib.jsonrpc_client import JsonRpcProxy, status_slugs_response_error_handler
from wacryptolib.keystore import generate_keypair_for_storage, ReadonlyFilesystemKeystore
from wacryptolib.utilities import load_from_json_bytes, generate_uuid0

from wacomponents.i18n import tr

Builder.load_file(str(Path(__file__).parent / 'decryption_request_form.kv'))


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

            self.ids.authenticator_checklist.add_widget(
                Factory.ListItemWithCheckbox(
                    text=tr._("Authenticator: {keystore_uid}").format(keystore_uid=keystore_uid))
            )

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
        readonly_filesystem_keystorage=ReadonlyFilesystemKeystore(local_keystore)

        print("local", local_keystore, type(local_keystore))
        response_keychain_uid = generate_uuid0()
        response_key_algo = "RSA_OAEP"
        generate_keypair_for_storage(key_algo=response_key_algo, keystore=local_keystore,
                                     keychain_uid=response_keychain_uid)
        response_public_key = readonly_filesystem_keystorage.get_public_key(keychain_uid=response_keychain_uid,
                                                                           key_algo=response_key_algo)
        return response_keychain_uid, response_key_algo, response_public_key

    def submit_decryption_request(self):

        gateway_proxy = self._get_gateway_proxy()

        cryptainers = self._get_cryptainers_with_cryptainer_names(self.selected_cryptainer_names)
        decryptable_symkeys_per_trustee = self.gather_decryptable_symkeys(cryptainers)
        description = self.ids.description.text
        response_keychain_uid, response_key_algo, response_public_key = self._create_and_return_response_keypair_from_local_factory()

        for trustee_id, decryptable_data in decryptable_symkeys_per_trustee.items():
            trustee_data, symkeys_data_to_decrypt = decryptable_data

            gateway_proxy.submit_decryption_request(keystore_uid=trustee_data["keystore_uid"], requester_uid=self.requester_uid,
                                                    description=description,
                                                    response_public_key=response_public_key,
                                                    response_keychain_uid=response_keychain_uid,
                                                    response_key_algo=response_key_algo,
                                                    symkeys_data_to_decrypt=symkeys_data_to_decrypt)
