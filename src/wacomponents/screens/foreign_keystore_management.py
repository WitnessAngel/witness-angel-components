import logging
import shutil
import uuid
from pathlib import Path

from kivy.factory import Factory
from kivy.lang import Builder
from kivy.properties import ObjectProperty
from kivymd.uix.button import MDFlatButton

from wacomponents.i18n import tr
from wacomponents.screens.base import WAScreenBase
from wacomponents.utilities import (
    format_authenticator_label,
    format_keypair_label,
    COLON,
    LINEBREAK,
    SPACE,
)
#from wacomponents.widgets.layout_components import build_fallback_information_box
from wacomponents.widgets.popups import (
    display_info_toast,
    close_current_dialog,
    dialog_with_close_button,
    safe_catch_unhandled_exception_and_display_popup,
)
from wacryptolib.authdevice import list_available_authdevices
from wacryptolib.authenticator import is_authenticator_initialized
from wacryptolib.exceptions import SchemaValidationError, ExistenceError, ValidationError
from wacryptolib.keystore import FilesystemKeystore, KEYSTORE_FORMAT, validate_keystore_tree

Builder.load_file(str(Path(__file__).parent / "foreign_keystore_management.kv"))


logger = logging.getLogger(__name__)


class ForeignKeystoreManagementScreen(WAScreenBase):
    filesystem_keystore_pool = ObjectProperty(None)

    def __init__(self, *args, **kwargs):
        self.selected_keystore_uids = []  # List of STRINGS
        self.register_event_type("on_selected_keyguardians_changed")
        super().__init__(*args, **kwargs)

    def on_selected_keyguardians_changed(self, *args):
        pass
        # print("I am dispatched on_selected_keyguardians_changed", args)

    @staticmethod
    def _check_if_auth_devices_connected_or_initialized():

        authdevices = list_available_authdevices()
        # print("DETECTED AUTH DEVICES", authdevices)

        close_current_dialog()
        if not authdevices:
            msg = tr._("No connected authentication devices found")
            display_info_toast(msg)
            return False
        else:
            authdevices_initialized = [x for x in authdevices if is_authenticator_initialized(x["authenticator_dir"])]

            if not authdevices_initialized:
                msg = tr._("No initialized authentication devices found")
                display_info_toast(msg)
                return False

        return authdevices_initialized

    @safe_catch_unhandled_exception_and_display_popup
    def import_keystores_from_usb(self, include_private_keys, authdevices_initialized):
        """
        loop through the “authdevices” present,
        and for those who are initialize, copy (with different Keystore for each folder)
        their content in a <KEYS_ROOT> / <keystore_uid> / folder (taking the keystore_uid from metadata.json)
        """

        logger.info("Importing foreign keystores from USB devices (include_private_keys=%s)", include_private_keys)

        foreign_keystore_metadata = []
        already_existing_keystore_metadata = []
        corrupted_keystore_count = 0

        for authdevice in authdevices_initialized:
            # print(">>>>>>>>>> importing,", authdevice)
            remote_keystore_dir = authdevice["authenticator_dir"]

            try:
                remote_keystore = FilesystemKeystore(remote_keystore_dir)
                keystore_tree = remote_keystore.export_to_keystore_tree(include_private_keys=include_private_keys)

                # Special operation: we remove optional sensitive data from this "foreign" keystore...
                for sensitive_key in ["keystore_secret", "keystore_passphrase_hint"]:
                    if sensitive_key in keystore_tree:
                        del keystore_tree[sensitive_key]

            except SchemaValidationError as exc:
                logger.warning("Corrupted keystore encountered: %r", exc)
                corrupted_keystore_count += 1
                continue

            try:

                updated = self.filesystem_keystore_pool.import_foreign_keystore_from_keystore_tree(keystore_tree)

                keystore_metadata = keystore_tree.copy()
                del keystore_metadata["keypairs"]

                if updated:
                    already_existing_keystore_metadata.append(keystore_metadata)
                else:
                    foreign_keystore_metadata.append(keystore_metadata)

            except ValidationError:  # Mismatch between keystore UIDs
                corrupted_keystore_count += 1

        msg = tr._(
            "{foreign_keystore_count} new authenticators imported, {already_existing_keystore_count} updated, {corrupted_keystore_count} skipped because corrupted"
        ).format(
            foreign_keystore_count=len(foreign_keystore_metadata),
            already_existing_keystore_count=len(already_existing_keystore_metadata),
            corrupted_keystore_count=corrupted_keystore_count,
        )

        # Autoselect freshly imported keys
        new_keystore_uids = [metadata["keystore_uid"] for metadata in foreign_keystore_metadata]
        self._change_authenticator_selection_status(keystore_uids=new_keystore_uids, is_selected=True)

        display_info_toast(msg)

        # update the display of authdevice saved in the local folder .keys_storage_ward
        self.list_foreign_keystores(display_toast=False)

    def open_keystore_deletion_dialog(self):

        keystore_uids = self.selected_keystore_uids
        if not keystore_uids:
            msg = tr._("Please select key guardians to remove")
            display_info_toast(msg)
            return

        message = tr._("Are you sure you want to remove %s key guardian(s)?") % len(keystore_uids)

        dialog_with_close_button(
            close_btn_label=tr._("Cancel"),
            title=tr._("Key guardian removal confirmation"),
            text=message,
            buttons=[
                MDFlatButton(
                    text=tr._("Confirm removal"),
                    on_release=lambda *args: (
                        close_current_dialog(),
                        self.delete_keystores(keystore_uids=keystore_uids),
                    ),
                )
            ],
        )

    @safe_catch_unhandled_exception_and_display_popup
    def delete_keystores(self, keystore_uids):

        logger.info("Deleting foreign keystores %s", keystore_uids)

        assert keystore_uids  # By construction

        # TODO move this to WACRYPTOLIB!
        for keystore_uid in keystore_uids:
            path = self.filesystem_keystore_pool._get_foreign_keystore_dir(keystore_uid)
            try:
                shutil.rmtree(path)
            except OSError as exc:
                logger.error("Failed deletion of imported authentication device %s: %r", keystore_uid, exc)

        self._change_authenticator_selection_status(
            keystore_uids=keystore_uids, is_selected=False
        )  # Update selection list

        msg = "Selected imported authentication devices were deleted"
        display_info_toast(msg)

        self.list_foreign_keystores(display_toast=False)

    @safe_catch_unhandled_exception_and_display_popup
    def list_foreign_keystores(self, display_toast=True):
        """
        loop through the KEYS_ROOT / files, and read their metadata.json,
        to display in the interface their USER and the start of their UUID

        KEYS_ROOT = “~/.keys_storage_ward/”
        """
        logger.debug("Listing foreign keystores")

        # print(">> we refresh auth devices panel")
        widget_ids = self.ids

        widget_ids.imported_authenticator_list.clear_widgets()
        widget_ids.imported_authenticator_list.do_layout()  # Prevents bug with "not found" message position

        keystore_metadata = self.filesystem_keystore_pool.get_all_foreign_keystore_metadata()

        if not keystore_metadata:
            return

        for (index, (keystore_uid, metadata)) in enumerate(sorted(keystore_metadata.items()), start=1):

            # So far, we're only dealing with AUTHENTICATORS here!

            authenticator_label = format_authenticator_label(
                authenticator_owner=metadata["keystore_owner"], keystore_uid=metadata["keystore_uid"], short_uid=True
            )

            foreign_authenticator_label = tr._("User") + " " + authenticator_label

            @safe_catch_unhandled_exception_and_display_popup
            def information_callback(
                keystore_uid, metadata=metadata
            ):  # Force keystore_uid save here, else scope bug
                self.display_keystore_details(keystore_uid=keystore_uid, keystore_owner=metadata["keystore_owner"])

            def selection_callback(  # FIXME make it class-level method
                keystore_uid, widget, value
            ):  # Force keystore_uid save here, else scope bug
                self.on_keystore_checkbox_click(keystore_uid=keystore_uid, is_selected=value)

            authenticator_entry = Factory.WASelectableListItemEntry(
                text=foreign_authenticator_label,
            )

            #print(">>>>>selected_keystore_uids is", self.selected_keystore_uids)
            data = dict(
                unique_identifier=str(keystore_uid),
                selection_callback=selection_callback,
                information_callback=information_callback,
                selected_unique_identifiers=self.selected_keystore_uids,
            )
            for key, value in data.items():
                setattr(authenticator_entry, key, value)

            widget_ids.imported_authenticator_list.add_widget(authenticator_entry)

        if display_toast:
            display_info_toast(tr._("Refreshed imported key guardians"))

    #def ____display_message_no_device_found(self):
    #    fallback_info_box = build_fallback_information_box("\n\n" + tr._("No imported authentication device found"))
    #    self.ids.imported_authenticator_list.add_widget(fallback_info_box)

    def on_keystore_checkbox_click(self, keystore_uid: uuid.UUID, is_selected: bool):
        self._change_authenticator_selection_status(keystore_uids=[keystore_uid], is_selected=is_selected)

    def _change_authenticator_selection_status(self, keystore_uids: list, is_selected: bool):
        for keystore_uid in keystore_uids:
            keystore_uid_str = str(keystore_uid)
            if not is_selected and keystore_uid_str in self.selected_keystore_uids:
                self.selected_keystore_uids.remove(keystore_uid_str)
            elif is_selected and keystore_uid_str not in self.selected_keystore_uids:
                self.selected_keystore_uids.append(keystore_uid_str)
        #print(">>>>>> on_selected_keyguardians_changed", self.selected_keystore_uids)
        self.dispatch("on_selected_keyguardians_changed", self.selected_keystore_uids)  # FIXME rename this
        # print("self.selected_keystore_uids", self.selected_keystore_uids)

    def display_keystore_details(self, keystore_uid, keystore_owner):

        foreign_metadata = self.filesystem_keystore_pool.get_foreign_keystore_metadata(keystore_uid=keystore_uid)

        foreign_keystore = self.filesystem_keystore_pool.get_foreign_keystore(keystore_uid=keystore_uid)
        keypair_identifiers = foreign_keystore.list_keypair_identifiers()

        message = (
            tr._("Type: {keystore_type}").format(keystore_type=foreign_metadata["keystore_type"].upper())
            + 2 * LINEBREAK
        )

        for index, keypair_identifier in enumerate(keypair_identifiers, start=1):
            private_key_present = keypair_identifier["private_key_present"]
            keypair_label = format_keypair_label(
                keychain_uid=keypair_identifier["keychain_uid"],
                key_algo=keypair_identifier["key_algo"],
                private_key_present=private_key_present,
                error_on_missing_key=False,
            )

            message += tr._("Key n°") + SPACE + str(index) + COLON() + keypair_label + LINEBREAK

        self.open_keystore_details_dialog(message, keystore_owner=keystore_owner)

    def open_keystore_details_dialog(self, message, keystore_owner):
        dialog_with_close_button(
            close_btn_label=tr._("Close"), title=tr._("Key Guardian %s") % keystore_owner, text=message
        )

    def show_import_key_from_web_dialog(self):

        dialog = dialog_with_close_button(
            close_btn_label=tr._("Cancel"),
            title=tr._("Import keys from web gateway"),
            type="custom",
            content_cls=Factory.AuthenticatorTesterContent(),  # FIXME WRONG
            buttons=[
                MDFlatButton(
                    text=tr._("Import"),
                    on_release=lambda *args: (
                        close_current_dialog(),
                        self.import_key_storage_from_web_gateway(dialog.content_cls.ids.tester_keystore_uid.text),
                    ),
                )
            ],
        )

    def choice_import_private_key_or_no_dialog(self):  # FIXME rename
        authdevices_initialized = self._check_if_auth_devices_connected_or_initialized()

        if authdevices_initialized:
            dialog_with_close_button(
                close_btn_label=tr._("Cancel"),
                title=tr._("Import keys from USB drives"),
                type="custom",
                content_cls=Factory.IncludePrivateKeysContent(),
                buttons=[
                    MDFlatButton(
                        text=tr._("Yes"),
                        on_release=lambda *args: (
                            close_current_dialog(),
                            self.import_keystores_from_usb(
                                include_private_keys=True, authdevices_initialized=authdevices_initialized
                            ),
                        ),
                    ),
                    MDFlatButton(
                        text=tr._("No"),
                        on_release=lambda *args: (
                            close_current_dialog(),
                            self.import_keystores_from_usb(
                                include_private_keys=False, authdevices_initialized=authdevices_initialized
                            ),
                        ),
                    ),
                ],
            )

    @staticmethod
    def _convert_public_authenticator_to_keystore_tree(public_authenticator):  # FIXME move that to wacryptolib?
        keypairs = []

        for public_key in public_authenticator["public_keys"]:
            keypairs.append(
                dict(
                    keychain_uid=public_key["keychain_uid"],
                    key_algo=public_key["key_algo"],
                    public_key=public_key["key_value"],
                    private_key=None,  # FIXME invalid
                )
            )

        keystore_tree = {
            "keystore_type": "authenticator",
            "keystore_format": KEYSTORE_FORMAT,
            "keystore_owner": public_authenticator["keystore_owner"],
            "keystore_uid": public_authenticator["keystore_uid"],
            "keypairs": keypairs,
        }
        if public_authenticator["keystore_creation_datetime"]:  # NULLABLE but always present
            keystore_tree["keystore_creation_datetime"] = public_authenticator["keystore_creation_datetime"]
        # No confidential fields, like passphrase hint or keystore secret, are present in public authenticator!
        validate_keystore_tree(keystore_tree)  # SAFETY
        return keystore_tree

    @safe_catch_unhandled_exception_and_display_popup
    def import_key_storage_from_web_gateway(self, keystore_uid_str):

        logger.debug("Importing foreign keystore %s from web gateway", keystore_uid_str)

        keystore_uid_str = keystore_uid_str.strip().lower()

        gateway_proxy = self._app.get_gateway_proxy()

        try:
            keystore_uid = uuid.UUID(keystore_uid_str)

            public_authenticator = gateway_proxy.get_public_authenticator(keystore_uid=keystore_uid)

            keystore_tree = self._convert_public_authenticator_to_keystore_tree(public_authenticator)

        except ValueError:  # FIXME dangerous position of this "except"
            result = tr._("Failure")
            details = tr._("Badly formed hexadecimal UUID string")

        except ExistenceError:
            result = tr._("Failure")
            details = tr._("Authenticator does not exist")

        else:
            self.filesystem_keystore_pool.import_foreign_keystore_from_keystore_tree(keystore_tree)

            msg = "Authentication device(s) updated"

            # Autoselect freshly imported keys

            new_keystore_uids = [keystore_tree["keystore_uid"]]
            self._change_authenticator_selection_status(keystore_uids=new_keystore_uids, is_selected=True)

            display_info_toast(msg)

            # update the display of authentication_device saved in the local folder .keys_storage_ward
            self.list_foreign_keystores(display_toast=False)

            result = tr._("Success")
            details = tr._("Authenticator has been imported successfully")

        dialog_with_close_button(title=tr._("Import result: %s") % result, text=details)
