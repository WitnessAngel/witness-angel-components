# This file is part of Witness Angel Components
# SPDX-FileCopyrightText: Copyright Prolifik SARL
# SPDX-License-Identifier: GPL-2.0-or-later

import logging
from pathlib import Path

from kivy.factory import Factory
from kivy.lang import Builder
from kivy.properties import ObjectProperty, BooleanProperty
from kivymd.uix.button import MDFlatButton

from wacomponents.default_settings import EXTERNAL_EXPORTS_DIR
from wacomponents.i18n import tr
from wacomponents.screens.base import WAScreenName, WAScreenBase
from wacomponents.utilities import (
    format_keypair_label,
    format_cryptainer_label,
    format_authenticator_label,
    SPACE,
    COLON,
    LINEBREAK,
)
#from wacomponents.widgets.layout_components import build_fallback_information_box
from wacomponents.widgets.popups import (
    dialog_with_close_button,
    close_current_dialog,
    safe_catch_unhandled_exception_and_display_popup,
    display_info_toast,
    display_info_snackbar,
)
from wacryptolib.cryptainer import gather_trustee_dependencies, get_trustee_id, CRYPTAINER_TRUSTEE_TYPES
from wacryptolib.exceptions import KeystoreDoesNotExist, KeyDoesNotExist, KeyLoadingError
from wacryptolib.keygen import load_asymmetric_key_from_pem_bytestring
from wacryptolib.keystore import load_keystore_metadata

Builder.load_file(str(Path(__file__).parent / "cryptainer_decryption_process.kv"))

logger = logging.getLogger(__name__)


class CryptainerDecryptionProcessScreen(WAScreenBase):
    selected_cryptainer_names = ObjectProperty(None, allownone=True)
    trustee_data = ObjectProperty(
        None, allownone=True
    )  # FIXME name not clear, i.e. "trustee_dependencies_for_encryption" ?
    filesystem_cryptainer_storage = ObjectProperty(None, allownone=True)
    filesystem_keystore_pool = ObjectProperty(None)
    ##found_trustees_lacking_passphrase = BooleanProperty(0)
    passphrase_mapper = {}

    has_last_decryption_info = BooleanProperty(False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.jsonrpc_url = self._app.get_wagateway_url()
        self.revelation_requestor_uid = self._app.get_wa_device_uid()

    def go_to_previous_screen(self):
        self.manager.current = WAScreenName.cryptainer_storage_management

    def get_container_summary(self):

        logger.debug("Refreshing the summary of concerned cryptainers")

        self.ids.selected_cryptainer_table.clear_widgets()

        """ Useless, hould nevr happen
        if not self.selected_cryptainer_names:
            fallback_info_box = build_fallback_information_box(tr._("No containers selected"))
            self.ids.selected_cryptainer_table.add_widget(fallback_info_box)
            return
        """

        for index, cryptainer_name in enumerate(reversed(self.selected_cryptainer_names), start=1):
            cryptainer_label = format_cryptainer_label(
                cryptainer_name=cryptainer_name
            )  # No need for Cryptainer ID here...
            cryptainer_entry_label = tr._("N°") + SPACE + str(index) + COLON() + cryptainer_label

            cryptainer_entry = Factory.WAListItemEntry(text=cryptainer_entry_label)  # FIXME RENAME THIS
            cryptainer_entry.unique_identifier = cryptainer_name

            self.ids.selected_cryptainer_table.add_widget(cryptainer_entry)

        display_info_toast(tr._("Refreshed concerned containers"))

    def _get_cryptainer_authenticator_dependency_status(
        self, keystore_uid, trustee_type, trustee_id, trustee_keypair_identifiers
    ):
        assert trustee_type == CRYPTAINER_TRUSTEE_TYPES.AUTHENTICATOR_TRUSTEE, trustee_type
        trustee_is_present = False
        trustee_status = tr._("not found")
        trustee_owner = None
        trustee_private_keys_missing = []
        passphrase_status = tr._("not set")

        try:
            filesystem_keystore = self.filesystem_keystore_pool.get_foreign_keystore(keystore_uid=keystore_uid)

            trustee_is_present = True
            trustee_status = tr._("found")

            foreign_keystore_dir = self.filesystem_keystore_pool._get_foreign_keystore_dir(keystore_uid=keystore_uid)
            metadata = load_keystore_metadata(foreign_keystore_dir)  # Might raise nasty exceptions ifcorruption
            trustee_owner = metadata["keystore_owner"]

            if self.passphrase_mapper.get(trustee_id):
                passphrase_status = tr._("set")

            for keypair_identifier in trustee_keypair_identifiers:
                try:
                    filesystem_keystore.get_private_key(**keypair_identifier)
                except KeyDoesNotExist:
                    trustee_private_keys_missing.append(keypair_identifier)
        except KeystoreDoesNotExist:
            pass

        status = dict(
            keystore_uid=keystore_uid,
            trustee_is_present=trustee_is_present,
            trustee_status=trustee_status,
            trustee_owner=trustee_owner,
            trustee_type=trustee_type,
            trustee_keypair_identifiers=trustee_keypair_identifiers,
            trustee_private_keys_missing=trustee_private_keys_missing,
            passphrase_status=passphrase_status,
        )

        return status

    def _get_cryptainers_with_cryptainer_names(
        self, cryptainer_names
    ):  # FIXME duplicated and not need as METHOD but FUNCTION
        cryptainers = []
        for cryptainer_name in cryptainer_names:
            cryptainer = self.filesystem_cryptainer_storage.load_cryptainer_from_storage(cryptainer_name)
            cryptainers.append(cryptainer)
        return cryptainers

    @safe_catch_unhandled_exception_and_display_popup
    def get_cryptainer_trustee_dependency_status(self):

        logger.debug("Refreshing the summary of trustee dependencies for cryptainers")

        self.ids.information_text.clear_widgets()

        if self.selected_cryptainer_names:

            cryptainers = self._get_cryptainers_with_cryptainer_names(self.selected_cryptainer_names)

            trustee_dependencies = gather_trustee_dependencies(cryptainers)

            trustee_data = list(trustee_dependencies["encryption"].values())
            trustee_data.sort(key=lambda x: x[0].get("keystore_owner", ""))  # No keystore owner for some trustee types

            self.trustee_data = trustee_data  # For launching of decryption

            for trustee_info, trustee_keypair_identifiers in trustee_data:
                trustee_id = get_trustee_id(trustee_info)
                trustee_type = trustee_info["trustee_type"]

                if trustee_type == CRYPTAINER_TRUSTEE_TYPES.AUTHENTICATOR_TRUSTEE:
                    keystore_uid = trustee_info["keystore_uid"]
                    status = self._get_cryptainer_authenticator_dependency_status(
                        keystore_uid,
                        trustee_type=trustee_type,
                        trustee_id=trustee_id,
                        trustee_keypair_identifiers=trustee_keypair_identifiers,
                    )
                    self._display_cryptainer_authenticator_dependency_status(status)
                else:
                    pass  # FIXME handle other types of trustee?

    def _display_cryptainer_authenticator_dependency_status(self, status):

        trustee_label = format_authenticator_label(
            authenticator_owner=status["trustee_owner"],
            trustee_type=status["trustee_type"],
            keystore_uid=status["keystore_uid"],
        )

        trustee_info = tr._("Key guardian") + COLON() + trustee_label

        trustee_present = tr._("Status") + COLON() + status["trustee_status"].upper()

        passphrase = tr._("passphrase") + COLON() + status["passphrase_status"].upper()

        if status["trustee_is_present"]:

            if status["trustee_private_keys_missing"]:
                trustee_keys_missing_labels = []
                for private_key_missing in status["trustee_private_keys_missing"]:
                    trustee_key_missing_label = format_keypair_label(**private_key_missing)
                    trustee_keys_missing_labels.append(trustee_key_missing_label)

                trustee_keys_missing_full_label = (
                    ", ".join(trustee_keys_missing_labels) if trustee_keys_missing_labels else tr._("None")
                )

                trustee_private_keys_status_text = (
                    tr._("Private key(s) missing locally")
                    + COLON()
                    + "{trustee_keys_missing_full_label}".format(
                        trustee_keys_missing_full_label=trustee_keys_missing_full_label
                    )
                )
            else:
                trustee_private_keys_status_text = tr._("Private keys needed for decryption are present")

        else:
            trustee_private_keys_status_text = tr._("Private keys needed were not found")

        dependencies_status_text = Factory.WAThreeListItemEntry(
            text=trustee_info,
            secondary_text=trustee_present + ", " + passphrase,
            tertiary_text=trustee_private_keys_status_text,
        )

        message = ""
        for index, keypair_identifier in enumerate(status["trustee_keypair_identifiers"], start=1):
            keypair_label = format_keypair_label(
                keychain_uid=keypair_identifier["keychain_uid"],
                key_algo=keypair_identifier["key_algo"],
                private_key_present=status["trustee_is_present"] and (keypair_identifier not in status["trustee_private_keys_missing"]),
                error_on_missing_key=False,
            )
            message += tr._("Keypair n°") + SPACE + str(index) + COLON() + keypair_label + LINEBREAK

        def information_callback(widget, message=message):
            self.show_trustee_keypair_identifiers(message=message)

        information_icon = dependencies_status_text.ids.information_icon
        information_icon.bind(on_press=information_callback)

        self.ids.information_text.add_widget(dependencies_status_text)

    def show_trustee_keypair_identifiers(self, message):
        dialog_with_close_button(close_btn_label=tr._("Close"), title=tr._("Keypairs used"), text=message)

    @safe_catch_unhandled_exception_and_display_popup
    def check_passphrase(self, passphrase):

        logger.info("Checking validity of submitted passphrase")  # DO NOT log the passphrase of course

        if [passphrase] in self.passphrase_mapper.values():
            result = tr._("Failure")
            details = tr._("Already existing passphrase") + COLON + passphrase

        else:
            # Default values
            result = tr._("Failure")
            details = tr._("Passphrase doesn't match any relevant private key")

            cryptainers = self._get_cryptainers_with_cryptainer_names(self.selected_cryptainer_names)

            dependencies = gather_trustee_dependencies(cryptainers)

            trustee_confs = [trustee[0] for trustee in dependencies["encryption"].values()]

            for trustee_conf in trustee_confs:

                if trustee_conf["trustee_type"] != CRYPTAINER_TRUSTEE_TYPES.AUTHENTICATOR_TRUSTEE:
                    continue  # This is not a trustee usable as foreign-keystore

                keystore_uid = trustee_conf["keystore_uid"]
                try:
                    filesystem_keystore = self.filesystem_keystore_pool.get_foreign_keystore(keystore_uid=keystore_uid)
                except KeystoreDoesNotExist:
                    continue  # Nothing to do if a trustee dependency is not found here

                keypair_identifiers = filesystem_keystore.list_keypair_identifiers()

                if not keypair_identifiers:
                    continue  # Keystore without keypairs in it

                # We test only the FIRST keypair of foreign keystore, assuming all are treated the same in it
                # TODO handle more finely keystores having different passphrases or presence per private key??
                keychain_uid = keypair_identifiers[0]["keychain_uid"]
                key_algo = keypair_identifiers[0]["key_algo"]

                try:
                    private_key_pem = filesystem_keystore.get_private_key(keychain_uid=keychain_uid, key_algo=key_algo)
                    key_obj = load_asymmetric_key_from_pem_bytestring(
                        key_pem=private_key_pem, key_algo=key_algo, passphrase=passphrase
                    )
                    assert key_obj, key_obj
                except (KeyLoadingError, KeyDoesNotExist):
                    pass  # This was not the right keystore
                else:
                    trustee_id = get_trustee_id(trustee_conf)
                    self.passphrase_mapper[trustee_id] = [
                        passphrase
                    ]  # For now we assume only ONE PASSPHRASE per trustee, here
                    result = tr._("Success")
                    details = tr._("Passphrase recognized")

        self.get_cryptainer_trustee_dependency_status()

        dialog_with_close_button(title=tr._("Validation result: %s") % result, text=details)

    def open_dialog_check_passphrase(self):  # FIXME RENAME

        dialog = dialog_with_close_button(
            close_btn_label=tr._("Cancel"),
            title=tr._("Add passphrase"),
            type="custom",
            content_cls=Factory.AddForeignPassphraseContent(),
            buttons=[
                MDFlatButton(
                    text=tr._("Check"),
                    on_release=lambda *args: (
                        close_current_dialog(),
                        self.check_passphrase(dialog.content_cls.ids.passphrase.text),
                    ),
                )
            ],
        )

    def decrypt_cryptainers_from_storage(self):

        logger.info("Attempting decryption of cryptainers")

        decrypted_cryptainer_count = 0
        decryption_results = []

        for cryptainer_name in self.selected_cryptainer_names:

            decryption_status = False

            try:

                result_payload, operation_report = self.filesystem_cryptainer_storage.decrypt_cryptainer_from_storage(
                    cryptainer_name,
                    passphrase_mapper=self.passphrase_mapper,
                    revelation_requestor_uid=self.revelation_requestor_uid,
                    gateway_urls=[self.jsonrpc_url],
                )

                if (
                        result_payload is not None
                ):  # Could be an empty bytestring though, after successful decryption of empty container
                    target_path = EXTERNAL_EXPORTS_DIR / (Path(cryptainer_name).with_suffix(""))
                    target_path.write_bytes(result_payload)
                    decryption_status = True
                    decrypted_cryptainer_count += 1
                    # print(">> Successfully exported data file to %s" % target_path)

                decryption_result_for_single_cryptainer = dict(
                    cryptainer_name=cryptainer_name,
                    decryption_status=decryption_status,
                    operation_report=operation_report,  # Might be empty if exception was raised, too...
                )
                decryption_results.append(decryption_result_for_single_cryptainer)

            except Exception as exc:
                message = "Abnormal error when decrypting container %s: %r" % (cryptainer_name, exc)
                logger.critical(message, exc_info=True)
                ### NOPE IMPOSSIBLE insubthread display_info_snackbar(message)

        decryption_info = (decrypted_cryptainer_count, decryption_results)
        return decryption_info

    @safe_catch_unhandled_exception_and_display_popup
    def decipher_cryptainers(self):
        assert self.filesystem_cryptainer_storage, self.filesystem_cryptainer_storage  # By construction...

        def resultat_callable(decryption_info, *args, **kwargs):  # FIXME CHANGE THIS NAME
            decrypted_cryptainer_count, decryption_results = decryption_info

            self.launch_remote_decryption_request_error_page(decryption_info)

            if not decrypted_cryptainer_count:

                message = tr._("All decryptions failed, see reports")
                display_info_snackbar(message)

        self._app._offload_task_with_spinner(self.decrypt_cryptainers_from_storage, resultat_callable)

    def launch_remote_decryption_request_error_page(self, decryption_info):
        # FIXME rename variables
        decryption_request_error_screen = self.manager.get_screen(WAScreenName.cryptainer_decryption_result)
        decryption_request_error_screen.last_decryption_info = decryption_info
        self.has_last_decryption_info = True  # Activate button to get back to that screen later
        self.manager.current = WAScreenName.cryptainer_decryption_result

    def launch_remote_decryption_request(self):
        _claimant_revelation_request_creation_form_screen_name = WAScreenName.claimant_revelation_request_creation_form
        remote_decryption_request_screen = self.manager.get_screen(
            _claimant_revelation_request_creation_form_screen_name
        )
        remote_decryption_request_screen.selected_cryptainer_names = self.selected_cryptainer_names
        remote_decryption_request_screen.trustee_data = self.trustee_data  # FIXME rename here too
        self.manager.current = _claimant_revelation_request_creation_form_screen_name
