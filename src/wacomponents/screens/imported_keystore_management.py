import logging
import secrets
import uuid

import shutil
import functools
from pathlib import Path

from kivy.factory import Factory
from kivy.lang import Builder
from kivy.properties import ObjectProperty
from kivy.uix import boxlayout
from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.config import Config
from kivy.properties import StringProperty, ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.screenmanager import ScreenManager
from kivy.uix.textinput import TextInput
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.app import MDApp
from kivymd.theming import ThemableBehavior
from kivymd.uix.button import MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import OneLineIconListItem, MDList
from kivymd.uix.screen import Screen
from kivymd.uix.snackbar import Snackbar

from wacryptolib.authenticator import is_authenticator_initialized
from wacryptolib.keystore import load_keystore_metadata, _get_keystore_metadata_file_path, _validate_keystore_metadata
from wacryptolib.authdevice import list_available_authdevices
from wacryptolib.exceptions import KeystoreAlreadyExists, SchemaValidationError, ExistenceError
from wacryptolib.utilities import dump_to_json_file
from wacryptolib.jsonrpc_client import JsonRpcProxy, status_slugs_response_error_handler
from jsonrpc_requests import JSONRPCError

from wacomponents.i18n import tr
from wacomponents.utilities import shorten_uid
from wacomponents.widgets.popups import display_info_toast, close_current_dialog, dialog_with_close_button

Builder.load_file(str(Path(__file__).parent / 'imported_keystore_management.kv'))


class AuthdeviceStoreScreen(Screen):
    filesystem_keystore_pool = ObjectProperty(None)

    jsonrpc_url = "http://127.0.0.1:8000" + "/json/"  # FIXME change url!!

    escrow_proxy = JsonRpcProxy(
        url=jsonrpc_url, response_error_handler=status_slugs_response_error_handler
    )

    def __init__(self, *args, **kwargs):
        self.selected_keystore_uids = []  # List of STRINGS
        self.register_event_type('on_selected_keyguardians_changed')
        super().__init__(*args, **kwargs)

    def on_selected_keyguardians_changed(self, *args):
        pass
        # print("I am dispatched on_selected_keyguardians_changed", args)

    def import_keystores_from_usb(self):
        """
        loop through the “authdevices” present,
        and for those who are initialize, copy (with different Keystore for each folder)
        their content in a <KEYS_ROOT> / <keystore_uid> / folder (taking the keystore_uid from metadata.json)
        """
        # list_devices = list_available_authdevices()
        # print(list_devices)
        # for index, authdevice in enumerate(list_devices):
        # print(">>>>>>>>>> import_keystores_from_usb started")
        authdevices = list_available_authdevices()
        # print("DETECTED AUTH DEVICES", authdevices)

        if not authdevices:
            msg = tr._("No connected authentication devices found")
        else:

            authdevices_initialized = [x for x in authdevices
                                       if is_authenticator_initialized(x["authenticator_dir"])]

            if not authdevices_initialized:
                msg = tr._("No initialized authentication devices found")

            else:

                imported_keystore_metadata = []
                already_existing_keystore_metadata = []
                corrupted_keystore_count = 0

                for authdevice in authdevices_initialized:
                    # print(">>>>>>>>>> importing,", authdevice)
                    remote_keystore_dir = authdevice["authenticator_dir"]

                    try:
                        keystore_metadata = load_keystore_metadata(remote_keystore_dir)
                    except SchemaValidationError:
                        corrupted_keystore_count += 1
                        continue

                    try:
                        self.filesystem_keystore_pool.import_keystore_from_filesystem(remote_keystore_dir)
                    except KeystoreAlreadyExists:
                        already_existing_keystore_metadata.append(keystore_metadata)
                    else:
                        imported_keystore_metadata.append(keystore_metadata)

                msg = tr._(
                    "{imported_keystore_count} authenticators properly imported, {already_existing_keystore_count} already existing, {corrupted_keystore_count} skipped because corrupted").format(
                    imported_keystore_count=len(imported_keystore_metadata),
                    already_existing_keystore_count=len(already_existing_keystore_metadata),
                    corrupted_keystore_count=corrupted_keystore_count
                )

                # Autoselect freshly imported keys
                new_keystore_uids = [metadata["keystore_uid"] for metadata in imported_keystore_metadata]
                self._change_authenticator_selection_status(keystore_uids=new_keystore_uids, is_selected=True)

        display_info_toast(msg)

        # update the display of authdevice saved in the local folder .keys_storage_ward
        self.list_imported_keystores(display_toast=False)

    def delete_keystores(self):

        # FIXME add confirmation dialog!!

        keystore_uids = self.selected_keystore_uids

        if not keystore_uids:
            msg = "Please select authentication devices to delete"
        else:
            # TODO move this to WACRYPTOLIB!
            for keystore_uid in keystore_uids:
                path = self.filesystem_keystore_pool._get_imported_keystore_dir(keystore_uid)
                try:
                    shutil.rmtree(path)
                except OSError as exc:
                    logging.error("Failed deletion of imported authentication device %s: %r", keystore_uid, exc)
            msg = "Selected imported authentication devices were deleted"

            self._change_authenticator_selection_status(keystore_uids=keystore_uids,
                                                        is_selected=False)  # Update selection list

        display_info_toast(msg)

        self.list_imported_keystores(display_toast=False)

    def list_imported_keystores(self, display_toast=True):
        """
        loop through the KEYS_ROOT / files, and read their metadata.json,
        to display in the interface their USER and the start of their UUID

        KEYS_ROOT = “~/.keys_storage_ward/”
        """
        # print(">> we refresh auth devices panel")
        Keys_page_ids = self.ids  # FIXME rename this

        Keys_page_ids.imported_authenticator_list.clear_widgets()  # FIXME naming
        Keys_page_ids.imported_authenticator_list.do_layout()  # Prevents bug with "not found" message position

        keystore_metadata = self.filesystem_keystore_pool.get_imported_keystore_metadata()

        if not keystore_metadata:
            self.display_message_no_device_found()
            return

        # self.chbx_lbls = {}  # FIXME: lbls ?
        # self.btn_lbls = {}  # FIXME: lbls ?

        for (index, (keystore_uid, metadata)) in enumerate(sorted(keystore_metadata.items()), start=1):
            keystore_uid_shortened = shorten_uid(keystore_uid)
            # print("COMPARING", str(keystore_uid), self.selected_keystore_uids)
            # my_check_box = CheckBox(
            #     active=(str(keystore_uid) in self.selected_keystore_uids),
            #     size_hint=(0.15, None),
            #     on_release=self.on_keystore_checkbox_click,
            #     height=40,
            # )
            # my_check_btn = Button(
            #     text="Key n°%s, User %s, Uid %s" % (index, metadata["keystore_owner"], uuid_suffix),
            #     size_hint=(0.85, None),
            #     #background_color=(0, 1, 1, 0.1),
            #     on_release=functools.partial(self.display_keystore_details, keystore_uid=keystore_uid, keystore_owner=metadata["keystore_owner"]),
            #     height=40,
            # )
            # self.chbx_lbls[my_check_box] = str(keystore_uid)
            # self.btn_lbls[my_check_btn] = str(keystore_uid)
            # device_row = BoxLayout(
            #    orientation="horizontal",
            # pos_hint={"center": 1, "top": 1},
            # padding=[20, 0],
            # )
            authenticator_label = tr._("User {keystore_owner}, id {keystore_uid}").format(
                keystore_owner=metadata["keystore_owner"], keystore_uid=keystore_uid_shortened)
            authenticator_entry = Factory.WASelectableListItemEntry(text=authenticator_label)  # FIXME RENAME THIS

            selection_checkbox = authenticator_entry.ids.selection_checkbox
            # print(">>>>>>>>selection_checkbox", selection_checkbox)
            selection_checkbox.active = str(keystore_uid) in self.selected_keystore_uids

            def selection_callback(widget, value,
                                   keystore_uid=keystore_uid):  # Force keystore_uid save here, else scope bug
                self.on_keystore_checkbox_click(keystore_uid=keystore_uid, is_selected=value)

            selection_checkbox.bind(active=selection_callback)

            information_icon = authenticator_entry.ids.information_icon

            def information_callback(widget, keystore_uid=keystore_uid,
                                     metadata=metadata):  # Force keystore_uid save here, else scope bug
                self.display_keystore_details(keystore_uid=keystore_uid, keystore_owner=metadata["keystore_owner"])

            information_icon.bind(on_press=information_callback)

            Keys_page_ids.imported_authenticator_list.add_widget(authenticator_entry)
            # Keys_page_ids.device_table.add_widget(my_check_btn)
            # Keys_page_ids.device_table.add_widget(device_row)

        if display_toast:
            display_info_toast(tr._("Refreshed imported authenticators"))
        """
                file_metadata = Path(dir_key_sorage).joinpath(".metadata.json")
                if file_metadata.exists():

                    metadata = load_from_json_file(file_metadata)
                    keystore_uid = str(metadata["keystore_uid"])
                    uuid = keystore_uid.split("-")
                    start_of_uuid = uuid[0].lstrip()
                    start_of_UUID = start_of_uuid.rstrip()
                    my_check_box = CheckBox(#start
                        active=False,
                        size_hint=(0.2, 0.2),
                        on_release=self.on_keystore_checkbox_click,
                    )
                    my_check_btn = Button(
                        text=" key N°:  %s        User:  %s      |      UUID device:  %s "
                        % ((str(index + 1)), str(metadata["keystore_owner"]), start_of_UUID),
                        size_hint=(0.8, 0.2),
                        background_color=(1, 1, 1, 0.01),
                        on_press=self.display_keystore_details,
                    )
                    self.chbx_lbls[my_check_box] = str(metadata["keystore_uid"])
                    self.btn_lbls[my_check_btn] = str(metadata["keystore_uid"])
                    layout = BoxLayout(
                        orientation="horizontal",
                        pos_hint={"center": 1, "top": 1},
                        padding=[140, 0]
                    )
                    layout.add_widget(my_check_box)
                    layout.add_widget(my_check_btn)
                    Keys_page_ids.table.add_widget(layout)
                    index += 1
                else:
                    self.display_message_no_device_found()
        """

    def display_message_no_device_found(self):

        # keys_page_ids = self.ids
        # devices_display = MDLabel(
        #     text="No imported autentication device found ",
        #     #background_color=(1, 0, 0, 0.01),
        #     halign="center",
        #     font_size="20sp",
        #     #color=[0, 1, 0, 1],
        # )
        # #keys_page_ids.imported_authenticator_list.clear_widgets()
        # Display_layout = MDBoxLayout(orientation="horizontal", padding=[140, 0])
        # Display_layout.add_widget(devices_display)

        Display_layout = Factory.WABigInformationBox()
        Display_layout.ids.inner_label.text = tr._("No imported authentication device found")
        keys_page_ids = self.ids
        keys_page_ids.imported_authenticator_list.add_widget(Display_layout)

    def on_keystore_checkbox_click(self, keystore_uid: uuid.UUID, is_selected: bool):
        self._change_authenticator_selection_status(keystore_uids=[keystore_uid], is_selected=is_selected, )

    def _change_authenticator_selection_status(self, keystore_uids: list, is_selected: bool):
        for keystore_uid in keystore_uids:
            keystore_uid_str = str(keystore_uid)
            if not is_selected and keystore_uid_str in self.selected_keystore_uids:
                self.selected_keystore_uids.remove(keystore_uid_str)
            elif is_selected and keystore_uid_str not in self.selected_keystore_uids:
                self.selected_keystore_uids.append(keystore_uid_str)
        self.dispatch('on_selected_keyguardians_changed', self.selected_keystore_uids)  # FIXME rename this
        # print("self.selected_keystore_uids", self.selected_keystore_uids)

    def display_keystore_details(self, keystore_uid, keystore_owner):

        """
        display the information of the keys stored in the selected usb

        """
        imported_keystore = self.filesystem_keystore_pool.get_imported_keystore(keystore_uid=keystore_uid)
        keypair_identifiers = imported_keystore.list_keypair_identifiers()

        message = ""
        for index, keypair_identifier in enumerate(keypair_identifiers, start=1):
            private_key_present_str = "Yes" if keypair_identifier["private_key_present"] else "No"
            uuid_suffix = shorten_uid(keypair_identifier["keychain_uid"])

            message += (
                    tr._("Key n° %s, %s: %s, private_key: %s\n")
                    % (
                        index,
                        keypair_identifier["key_algo"],
                        uuid_suffix,
                        private_key_present_str,
                    )
                    + "\n"
            )
        self.open_keystore_details_dialog(message, keystore_owner=keystore_owner)

    def open_keystore_details_dialog(self, message, keystore_owner):
        dialog_with_close_button(
            close_btn_label=tr._("Close"),
            title=tr._("Key Guardian %s") % keystore_owner,
            text=message,
        )

    def show_import_key_from_web_dialog(self):

        dialog = dialog_with_close_button(
            close_btn_label=tr._("Cancel"),
            title=tr._("Import keys from web"),
            type="custom",
            content_cls=Factory.AuthenticatorTesterContent(),
            buttons=[
                MDFlatButton(text=tr._("Import"),
                             on_release=lambda *args: self.import_key_storage_from_data_tree(dialog))],
        )

    @staticmethod
    def _dump_metadata_to_folder(imported_key_storage_path: Path, public_authenticator: dict):
        metadata_file = _get_keystore_metadata_file_path(imported_key_storage_path)
        metadata_file.parent.mkdir(parents=True, exist_ok=True)  # FIXME Create a temporary folder
        metadata = {}
        metadata.update(
            {"keystore_type": "authenticator",
             "keystore_format": "keystore_1.0",
             "keystore_uid": public_authenticator["keystore_uid"],
             "keystore_owner": public_authenticator["keystore_owner"],
             "keystore_secret": secrets.token_urlsafe(64),
             })
        _validate_keystore_metadata(metadata)
        dump_to_json_file(metadata_file, metadata)
        return metadata

    def import_key_storage_from_data_tree(self, dialog):
        keystore_str = dialog.content_cls.ids.tester_keystore_uid.text
        close_current_dialog()
        try:

            keystore_uid = uuid.UUID(keystore_str)

            try:
                self.filesystem_keystore_pool.ensure_imported_keystore_does_not_exist(keystore_uid)

            except KeystoreAlreadyExists:
                result = tr._("Failure")
                details = tr._("Key storage with UUID %s was already imported locally" % keystore_uid)

            else:
                try:
                    public_authenticator = self.escrow_proxy.get_public_authenticator_view(keystore_uid=keystore_uid)

                except ExistenceError:
                    result = tr._("Failure")
                    details = tr._("Authenticator does not exist")

                except (JSONRPCError, OSError):
                    result = tr._("Failure")
                    details = tr._("Error calling method, check the server url")

                else:

                    imported_keystore_dir = self.filesystem_keystore_pool._get_imported_keystore_dir(
                        keystore_uid=keystore_uid)

                    self._dump_metadata_to_folder(imported_keystore_dir, public_authenticator)

                    filesystem_keystore = self.filesystem_keystore_pool.get_imported_keystore(keystore_uid=keystore_uid)

                    for public_key in public_authenticator["public_keys"]:
                        filesystem_keystore.set_keys_from_web(
                            keychain_uid=public_key["keychain_uid"],
                            key_algo=public_key["key_algo"],
                            public_key=public_key["payload"],
                        )

                    assert imported_keystore_dir.exists()

                    msg = "An authentication device(s) updated"

                    # Autoselect freshly imported keys

                    new_keystore_uids = [public_authenticator["keystore_uid"]]
                    self._change_authenticator_selection_status(keystore_uids=new_keystore_uids, is_selected=True)

                    display_info_toast(msg)

                    # update the display of authentication_device saved in the local folder .keys_storage_ward
                    self.list_imported_keystores(display_toast=False)

                    result = tr._("Success")
                    details = tr._("Authenticator has been imported successfully")

        except ValueError:
            result = tr._("Failure")
            details = tr._("Badly formed hexadecimal UUID string")

        dialog_with_close_button(
            title=tr._("Checkup result: %s") % result,
            text=details,
        )
