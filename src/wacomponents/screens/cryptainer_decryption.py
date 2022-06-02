from pathlib import Path

from kivy.factory import Factory
from kivy.lang import Builder
from kivy.properties import ObjectProperty, BooleanProperty
from kivymd.uix.button import MDFlatButton
from kivymd.uix.screen import Screen
from kivymd.uix.snackbar import Snackbar

from wacomponents.default_settings import EXTERNAL_EXPORTS_DIR
from wacomponents.i18n import tr
from wacomponents.utilities import shorten_uid
from wacomponents.widgets.popups import dialog_with_close_button, close_current_dialog, \
    safe_catch_unhandled_exception_and_display_popup, display_info_toast
from wacryptolib.cryptainer import gather_trustee_dependencies, get_trustee_id, \
    CRYPTAINER_TRUSTEE_TYPES
from wacryptolib.exceptions import KeystoreDoesNotExist, KeyDoesNotExist, KeyLoadingError
from wacryptolib.keygen import load_asymmetric_key_from_pem_bytestring
from wacryptolib.keystore import load_keystore_metadata

Builder.load_file(str(Path(__file__).parent / 'cryptainer_decryption.kv'))

from kivy.logger import Logger as logger


class CryptainerDecryptionScreen(Screen):
    selected_cryptainer_names = ObjectProperty(None, allownone=True)
    filesystem_cryptainer_storage = ObjectProperty(None, allownone=True)
    filesystem_keystore_pool = ObjectProperty(None)
    ##found_trustees_lacking_passphrase = BooleanProperty(0)
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

        display_info_toast(tr._("Refreshed concerned containers"))

    def _get_cryptainer_trustee_dependency_status(self, keystore_uid, trustee_type, trustee_id, trustee_keypair_identifiers):

        trustee_is_present = False
        trustee_status = tr._("NOT found")
        trustee_owner = None
        trustee_private_keys_missing = []
        passphrase_status = tr._("NOT set")

        try:
            filesystem_keystore = self.filesystem_keystore_pool.get_foreign_keystore(keystore_uid=keystore_uid)

            trustee_is_present = True
            trustee_status = tr._("Found")

            foreign_keystore_dir = self.filesystem_keystore_pool._get_foreign_keystore_dir(keystore_uid=keystore_uid)
            metadata = load_keystore_metadata(foreign_keystore_dir)
            trustee_owner = metadata["keystore_owner"]

            if self.passphrase_mapper.get(trustee_id):
                passphrase_status = tr._("Set")
                ##self.found_trustees_lacking_passphrase = False
            else:
                pass
                ##self.found_trustees_lacking_passphrase = True

            for keypair_identifier in trustee_keypair_identifiers:
                try:
                    filesystem_keystore.get_private_key(**keypair_identifier)
                except KeyDoesNotExist:
                    trustee_private_keys_missing.append(keypair_identifier)
        except KeystoreDoesNotExist:
            pass

        status = dict(
            keystore_uid=shorten_uid(keystore_uid),
            trustee_is_present=trustee_is_present,
            trustee_status=trustee_status,
            trustee_owner=trustee_owner,
            trustee_type=trustee_type,
            trustee_keypair_identifiers=trustee_keypair_identifiers,
            trustee_private_keys_missing=trustee_private_keys_missing,
            passphrase_status=passphrase_status,
        )

        return status

    def _get_cryptainers_with_cryptainer_names(self, cryptainer_names):
        cryptainers = []
        for cryptainer_name in cryptainer_names:
            cryptainer = self.filesystem_cryptainer_storage.load_cryptainer_from_storage(cryptainer_name)
            cryptainers.append(cryptainer)
        return cryptainers

    @safe_catch_unhandled_exception_and_display_popup
    def get_cryptainer_trustee_dependency_status(self):
        self.ids.information_text.clear_widgets()

        if self.selected_cryptainer_names:

            cryptainers = self._get_cryptainers_with_cryptainer_names(self.selected_cryptainer_names)

            trustee_dependencies = gather_trustee_dependencies(cryptainers)

            # print(list(trustee_dependencies["encryption"].values()))

            trustee_data = [trustee for trustee in trustee_dependencies["encryption"].values()]

            for trustee_info, trustee_keypair_identifiers in trustee_data:
                trustee_id = get_trustee_id(trustee_info)
                trustee_type = trustee_info["trustee_type"]
                keystore_uid = trustee_info["keystore_uid"]

                if trustee_type == CRYPTAINER_TRUSTEE_TYPES.AUTHENTICATOR_TRUSTEE:  # FIXME utiliser Enums python TrusteeTypes.xxx
                    status = self._get_cryptainer_trustee_dependency_status(keystore_uid, trustee_type=trustee_type, trustee_id=trustee_id, trustee_keypair_identifiers=trustee_keypair_identifiers)
                    self._display_cryptainer_trustee_dependency_status(status)
                else:
                    pass  # FIXME handle other types of trustee?

    def _display_cryptainer_trustee_dependency_status(self, status):

        trustee_data = tr._("{trustee_type} {keystore_uid}").format(**status)
        trustee_present = tr._("Key guardian: {trustee_status}").format(**status)
        trustee_private_keys_missing_text = ""
        passphrase = tr._("Passphrase: {passphrase_status}").format(**status)
        trustee_owner = ""
        if status["trustee_is_present"]:
            trustee_owner = " " + tr._("(Owner: {trustee_owner})").format(**status)
            if status["trustee_private_keys_missing"]:
                trustee_private_keys_missing_text = tr._("Missing private key(s): {trustee_keys_missing}").format(
                    trustee_keys_missing=", ".join(shorten_uid(keypair_identifier["keychain_uid"])
                                                   for keypair_identifier in status["trustee_private_keys_missing"]))

        dependencies_status_text = Factory.WAThreeListItemEntry(text=trustee_data + trustee_owner, secondary_text=trustee_present + ', ' + passphrase, tertiary_text=trustee_private_keys_missing_text)  # FIXME RENAME THIS

        message = ""
        for index, keypair_identifier in enumerate(status["trustee_keypair_identifiers"], start=1):
            message += tr._("Key n° {index}: type {key_algo}, uid ...{keychain_uid}\n").format(
                index=index,
                key_algo=keypair_identifier["key_algo"],
                keychain_uid=shorten_uid(keypair_identifier["keychain_uid"])
            )

        def information_callback(widget, message=message):
            self.show_trustee_keypair_identifiers(message=message)

        information_icon = dependencies_status_text.ids.information_icon
        information_icon.bind(on_press=information_callback)

        self.ids.information_text.add_widget(dependencies_status_text)

    def show_trustee_keypair_identifiers(self, message):
        dialog_with_close_button(
            close_btn_label=tr._("Close"),
            title=tr._("Keypairs used"),
            text=message,
        )

    @safe_catch_unhandled_exception_and_display_popup
    def check_passphrase(self, passphrase):

        close_current_dialog()

        if [passphrase] in self.passphrase_mapper.values():
            result = tr._("Failure")
            details = tr._("Already existing passphrase %s" % (passphrase))

        else:
            # Default values
            result = tr._("Failure")
            details = tr._("Passphrase doesn't match any relevant private key")

            cryptainers = self._get_cryptainers_with_cryptainer_names(self.selected_cryptainer_names)

            dependencies = gather_trustee_dependencies(cryptainers)

            trustee_confs = [trustee[0] for trustee in dependencies["encryption"].values()]

            for trustee_conf in trustee_confs:
                keystore_uid = trustee_conf["keystore_uid"]
                try:
                    filesystem_keystore = self.filesystem_keystore_pool.get_foreign_keystore(keystore_uid=keystore_uid)
                except KeystoreDoesNotExist:
                    continue

                keypair_identifiers = filesystem_keystore.list_keypair_identifiers()

                if not keypair_identifiers:
                    continue  # Keystore without keypairs in it

                # We test only the FIRST keypair of foreign keystore, assuming all are treated the same in it
                # TODO handle more finely keystores having different passphrases or presence per private key??
                keychain_uid = keypair_identifiers[0]["keychain_uid"]
                key_algo = keypair_identifiers[0]["key_algo"]

                try:
                    private_key_pem = filesystem_keystore.get_private_key(keychain_uid=keychain_uid, key_algo=key_algo)
                    key_obj = load_asymmetric_key_from_pem_bytestring(key_pem=private_key_pem, key_algo=key_algo, passphrase=passphrase)
                    assert key_obj, key_obj
                except (KeyLoadingError, KeyDoesNotExist):
                    pass  # This was not the right keystore
                else:
                    trustee_id = get_trustee_id(trustee_conf)
                    self.passphrase_mapper[trustee_id] = [passphrase]  # For now we assume only ONE PASSPHRASE per trustee, here
                    result = tr._("Success")
                    details = tr._("Passphrase recognized")

        self.get_cryptainer_trustee_dependency_status()
        dialog_with_close_button(
            title=tr._("Checkup result: %s") % result,
            text=details,
        )

    def open_dialog_check_passphrase(self):  # FIXME RENAME
        dialog = dialog_with_close_button(
            close_btn_label=tr._("Cancel"),
            title=tr._("Check passphrase"),
            type="custom",
            content_cls=Factory.CheckPassphraseContent(),
            buttons=[
                MDFlatButton(text=tr._("Check"),
                             on_release=lambda *args: self.check_passphrase(dialog.content_cls.ids.passphrase.text))],
        )

    @safe_catch_unhandled_exception_and_display_popup
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
                logger.warning("Error decrypting container %s: %r" % (cryptainer_name, exc))
                errors.append(exc)

        if errors:
            message = "Errors happened during decryption, see logs"  # TODO TRADUIRE
        else:
            message = "Decryption successful, see export folder for results"  # TODO TRADUIRE

        Snackbar(
            text=message,
            font_size="12sp",
            duration=5,
        ).open()
