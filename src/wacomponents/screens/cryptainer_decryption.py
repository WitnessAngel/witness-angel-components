from pathlib import Path
from pprint import pprint

from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivymd.app import MDApp
from kivymd.uix.button import MDFlatButton
from kivymd.uix.snackbar import Snackbar
from wacryptolib.cryptainer import gather_trustee_dependencies, request_decryption_authorizations, _get_trustee_id
from kivy.properties import StringProperty, ListProperty, ObjectProperty
from wacryptolib.exceptions import KeystoreDoesNotExist, KeyDoesNotExist, KeyLoadingError
from wacryptolib.keygen import load_asymmetric_key_from_pem_bytestring
from wacryptolib.keystore import FilesystemKeystore

from wacomponents.default_settings import EXTERNAL_EXPORTS_DIR
from wacomponents.i18n import tr
from kivy.factory import Factory
from wacomponents.widgets.popups import dialog_with_close_button, close_current_dialog

Builder.load_file(str(Path(__file__).parent / 'cryptainer_decryption.kv'))


class CryptainerDecryptionScreen(Screen):
    filesystem_cryptainer_storage = ObjectProperty(None, allownone=True)
    filesystem_keystore_pool = ObjectProperty(None)
    passphrase_mapper = {}

    def go_to_previous_screen(self):
        self.manager.current = "CryptainerManagement"

    def get_container_summary(self):
        cryptainer_management_screen = self.manager.get_screen("CryptainerManagement")
        cryptainer_names = cryptainer_management_screen._get_selected_cryptainer_names()

        for index, cryptainer_name in enumerate(cryptainer_names, start=1):  # TODO Create a private function
            cryptainer_label = tr._("N° %s:  %s") % (index, cryptainer_name)
            cryptainer_entry = Factory.WASelectableListItemEntry(text=cryptainer_label)  # FIXME RENAME THIS
            cryptainer_entry.unique_identifier = cryptainer_name

            # selection_checkbox = container_entry.ids.selection_checkbox

            # def selection_callback(widget, value, container_name=container_name):  # Force container_name save here, else scope bug
            #    self.check_box_authentication_device_checked(device_uid=device_uid, is_selected=value)
            # selection_checkbox.bind(active=selection_callback)

            def information_callback(widget,
                                     cryptainer_name=cryptainer_name):  # Force device_uid save here, else scope bug
                cryptainer_management_screen.show_container_details(cryptainer_name=cryptainer_name)

            information_icon = cryptainer_entry.ids.information_icon
            information_icon.bind(on_press=information_callback)

            self.ids.selected_cryptainer_table.add_widget(cryptainer_entry)

    def check_passphrase(self, dialog):

        cryptainer_management_screen = self.manager.get_screen("CryptainerManagement")
        cryptainer_names = cryptainer_management_screen._get_selected_cryptainer_names()

        passphrase = dialog.content_cls.ids.passphrase.text
        cryptainers = []

        for cryptainer_name in cryptainer_names:
            cryptainer = self.filesystem_cryptainer_storage.load_cryptainer_from_storage(cryptainer_name)
            cryptainers.append(cryptainer)

        dependencies = gather_trustee_dependencies(cryptainers)
        # print(dependencies)

        relevant_keystore_uids = [trustee[0]["keystore_uid"] for trustee in dependencies["encryption"].values()]
        # print(relevant_keystore_uids)
        for keystore_uid in relevant_keystore_uids:
            try:
                filesystem_keystore = self.filesystem_keystore_pool.get_imported_keystore(keystore_uid=keystore_uid)
                keypair_identifiers = filesystem_keystore.list_keypair_identifiers()
                # print(keypair_identifiers)

            except KeystoreDoesNotExist:
                result = tr._("Failure")
                details = tr._("Key storage does not exist")

            else:
                keychain_uid = keypair_identifiers[0]["keychain_uid"]
                key_algo = keypair_identifiers[0]["key_algo"]
                try:
                    private_key_pem = filesystem_keystore.get_private_key(keychain_uid=keychain_uid, key_algo=key_algo)
                    key_obj = load_asymmetric_key_from_pem_bytestring(
                        key_pem=private_key_pem, key_algo=key_algo, passphrase=passphrase
                    )
                    assert key_obj, key_obj

                    trustee_conf = [trustee[0] for trustee in dependencies["encryption"].values()]
                    trustee_id = _get_trustee_id(trustee_conf[0])
                    self.passphrase_mapper[trustee_id] = [passphrase]
                    result = tr._("Success")
                    details = tr._("Accepted passphrase")

                except KeyDoesNotExist:
                    result = tr._("Failure")
                    details = tr._("Private key does not exist")

                except KeyLoadingError:
                    result = tr._("Failure")
                    details = tr._("Failed loading key from pem bytestring with passphrase")

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

    def decipher_cryptainers(self, cryptainer_names, input_content_cls):
        assert self.filesystem_cryptainer_storage, self.filesystem_cryptainer_storage  # By construction...

        inputs = list(reversed(input_content_cls.children))
        passphrases = [i.text for i in inputs]
        passphrase_mapper = {None: passphrases}  # For now we regroup all passphrases together

        errors = []

        for cryptainer_name in cryptainer_names:
            try:
                EXTERNAL_EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
                # FIXME make this asynchronous, to avoid stalling the app!
                result = self.filesystem_cryptainer_storage.decrypt_cryptainer_from_storage(cryptainer_name,
                                                                                            passphrase_mapper=passphrase_mapper)
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

    def verify_escrows(self):
        pass
