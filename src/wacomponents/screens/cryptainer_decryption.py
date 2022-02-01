from pathlib import Path
from pprint import pprint
from textwrap import dedent

from kivy.lang import Builder
from kivy.uix.textinput import TextInput
from kivymd.uix.screen import Screen
from kivymd.app import MDApp
from kivymd.uix.button import MDFlatButton
from kivymd.uix.snackbar import Snackbar
from wacryptolib.cryptainer import gather_trustee_dependencies, request_decryption_authorizations, _get_trustee_id, \
    CRYPTAINER_TRUSTEE_TYPES
from kivy.properties import StringProperty, ListProperty, ObjectProperty, NumericProperty
from wacryptolib.exceptions import KeystoreDoesNotExist, KeyDoesNotExist, KeyLoadingError
from wacryptolib.keygen import load_asymmetric_key_from_pem_bytestring
from wacryptolib.keystore import FilesystemKeystore, load_keystore_metadata

from wacomponents.default_settings import EXTERNAL_EXPORTS_DIR
from wacomponents.i18n import tr
from kivy.factory import Factory

from wacomponents.utilities import shorten_uid
from wacomponents.widgets.popups import dialog_with_close_button, close_current_dialog

Builder.load_file(str(Path(__file__).parent / 'cryptainer_decryption.kv'))


class CryptainerDecryptionScreen(Screen):
    selected_cryptainer_names = ObjectProperty(None, allownone=True)
    filesystem_cryptainer_storage = ObjectProperty(None, allownone=True)
    filesystem_keystore_pool = ObjectProperty(None)
    found_trustees_lacking_passphrase = NumericProperty(0)
    passphrase_mapper = {}

    def go_to_previous_screen(self):
        self.manager.current = "CryptainerManagement"

    def get_container_summary(self):
        self.ids.selected_cryptainer_table.clear_widgets()

        if not self.selected_cryptainer_names:
            display_layout = Factory.WABigInformationBox()
            display_layout.ids.inner_label.text = tr._("No containers selected")
            self.ids.selected_cryptainer_table.add_widget(display_layout)
            return

        for index, cryptainer_name in enumerate(reversed(self.selected_cryptainer_names), start=1):
            cryptainer_label = tr._("N° {index}: {cryptainer_name}").format(index=index, cryptainer_name=cryptainer_name)
            cryptainer_entry = Factory.WAListItemEntry(text=cryptainer_label)  # FIXME RENAME THIS
            cryptainer_entry.unique_identifier = cryptainer_name

            self.ids.selected_cryptainer_table.add_widget(cryptainer_entry)

    def _get_cryptainer_trustee_dependency_status(self, trustee_uid, trustee_type, trustee_id):
        trustee_keys_missing = []
        passphrase = tr._("NOT Set")

        try:
            filesystem_keystore = self.filesystem_keystore_pool.get_imported_keystore(keystore_uid=trustee_uid)

            imported_keystore_dir = self.filesystem_keystore_pool._get_imported_keystore_dir(keystore_uid=trustee_uid)
            metadata = load_keystore_metadata(imported_keystore_dir)
            keystore_owner = metadata["keystore_owner"]

            if trustee_id in self.passphrase_mapper:
                passphrase = tr._("Set")
                self.found_trustees_lacking_passphrase = 0
            else:
                self.found_trustees_lacking_passphrase = 1

            keypair_identifiers = filesystem_keystore.list_keypair_identifiers()
            for keypair_identifier in keypair_identifiers:
                if keypair_identifier["private_key_present"] == False:
                    trustee_keys_missing.append(keypair_identifier["keychain_uid"])

            status = dict(trustee_data=shorten_uid(trustee_uid),
                          keystore_owner=keystore_owner,
                          trustee_type=trustee_type,
                          trustee_present=tr._("Found"),
                          passphrase=passphrase,
                          trustee_keys_missing=trustee_keys_missing
                          )
        except KeystoreDoesNotExist:
            status = dict(trustee_data=shorten_uid(trustee_uid),
                          trustee_type=trustee_type,
                          trustee_present=tr._("NOT Found"),
                          passphrase=passphrase,
                          )

        return status

    def _get_cryptainers_with_cryptainer_names(self, cryptainer_names):
        cryptainers = []
        for cryptainer_name in cryptainer_names:
            cryptainer = self.filesystem_cryptainer_storage.load_cryptainer_from_storage(cryptainer_name)
            cryptainers.append(cryptainer)
        return cryptainers

    def get_cryptainer_trustee_dependency_status(self) -> dict:
        self.ids.information_text.clear_widgets()

        if self.selected_cryptainer_names:

            cryptainers = self._get_cryptainers_with_cryptainer_names(self.selected_cryptainer_names)

            trustee_dependencies = gather_trustee_dependencies(cryptainers)

            trustee_conf = [trustee[0] for trustee in trustee_dependencies["encryption"].values()]
            trustee_id = _get_trustee_id(trustee_conf[0])

            for trustee in trustee_conf:
                trustee_uid = trustee["keystore_uid"]
                trustee_type = trustee["trustee_type"]

                if trustee_type == CRYPTAINER_TRUSTEE_TYPES.AUTHENTICATOR_TRUSTEE:  # FIXME utiliser Enums python TrusteeTypes.xxx

                    status = self._get_cryptainer_trustee_dependency_status(trustee_uid, trustee_type, trustee_id)

                else:
                    # FIXME add the case if trustee_type != "authenticator"
                    continue
                self._display_cryptainer_trustee_dependency_status(status)

    def _display_cryptainer_trustee_dependency_status(self, status):

        trustee_data = tr._(" {trustee_type}: {trustee_data}").format(trustee_type=status["trustee_type"],
                                                                      trustee_data=status["trustee_data"])
        trustee_present = tr._(" Trustee: {trustee_present}").format(trustee_present=status["trustee_present"])
        trustee_keys_missing = ""
        passphrase = tr._(" Passphrase: {passphrase}").format(passphrase=status["passphrase"])
        trustee_owner = ""
        if status["trustee_present"] == "Found":
            trustee_owner = tr._("( Owner: {trustee_owner})").format(trustee_owner=status["keystore_owner"])
            if status["trustee_keys_missing"]:
                trustee_keys_missing = tr._(" Missing key(s): {trustee_keys_missing}").format(
                    trustee_keys_missing=status["trustee_keys_missing"])

        dependencies_status_text = Factory.WAThreeListItemEntry(text=trustee_data + trustee_owner , secondary_text=trustee_present + ',' + passphrase, tertiary_text=trustee_keys_missing)  # FIXME RENAME THIS

        self.ids.information_text.add_widget(dependencies_status_text)

    def check_passphrase(self, dialog):

        passphrase = dialog.content_cls.ids.passphrase.text

        if [passphrase] in self.passphrase_mapper.values():
            result = tr._("Failure")
            details = tr._("Already existing passphrase %s" % (passphrase))

        else:

            cryptainers = self._get_cryptainers_with_cryptainer_names(self.selected_cryptainer_names)

            dependencies = gather_trustee_dependencies(cryptainers)

            relevant_keystore_uids = [trustee[0]["keystore_uid"] for trustee in dependencies["encryption"].values()]
            for keystore_uid in relevant_keystore_uids:

                filesystem_keystore = self.filesystem_keystore_pool.get_imported_keystore(keystore_uid=keystore_uid)
                keypair_identifiers = filesystem_keystore.list_keypair_identifiers()

                keychain_uid = keypair_identifiers[0]["keychain_uid"]
                key_algo = keypair_identifiers[0]["key_algo"]
                try:
                    private_key_pem = filesystem_keystore.get_private_key(keychain_uid=keychain_uid, key_algo=key_algo)
                    key_obj = load_asymmetric_key_from_pem_bytestring(key_pem=private_key_pem, key_algo=key_algo, passphrase=passphrase)
                    assert key_obj, key_obj

                    trustee_conf = [trustee[0] for trustee in dependencies["encryption"].values()]
                    trustee_id = _get_trustee_id(trustee_conf[0])
                    self.passphrase_mapper[trustee_id] = [passphrase]
                    result = tr._("Success")
                    details = tr._("Accepted passphrase")

                except KeyLoadingError:
                    result = tr._("Failure")
                    details = tr._("Failed loading key from pem bytestring with passphrase")

                except KeyDoesNotExist:
                    result = tr._("Failure")
                    details = tr._("Private key does not exist")

        self.get_cryptainer_trustee_dependency_status()

        close_current_dialog()

        dialog_with_close_button(
            title=tr._("Checkup result: %s") % result,
            text=details,
        )

    def open_dialog_check_passphrase(self):
        dialog = dialog_with_close_button(
            close_btn_label=tr._("Cancel"),
            title=tr._("Check passphrase"),
            type="custom",
            content_cls=Factory.CheckPassphraseContent(),
            buttons=[
                MDFlatButton(text=tr._("Check"),
                             on_release=lambda *args: self.check_passphrase(dialog))],
        )

    def decipher_cryptainers(self):
        assert self.filesystem_cryptainer_storage, self.filesystem_cryptainer_storage  # By construction...

        errors = []

        for cryptainer_name in self.selected_cryptainer_names:
            try:
                EXTERNAL_EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
                # FIXME make this asynchronous, to avoid stalling the app!
                result = self.filesystem_cryptainer_storage.decrypt_cryptainer_from_storage(cryptainer_name, passphrase_mapper=self.passphrase_mapper)
                target_path = EXTERNAL_EXPORTS_DIR / (Path(cryptainer_name).with_suffix(""))
                target_path.write_bytes(result)
                # print(">> Successfully exported data file to %s" % target_path)
            except Exception as exc:
                # print(">>>>> close_dialog_decipher_cryptainer() exception thrown:", exc)  # TEMPORARY
                errors.append(exc)

        if errors:
            message = "Errors happened during decryption, see logs"
        else:
            message = "Decryption successful, see export folder for results"

        Snackbar(
            text=message,
            font_size="12sp",
            duration=5,
        ).open()
