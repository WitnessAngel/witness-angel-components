import logging
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
from waguilib.i18n import tr

from wacryptolib.authentication_device import list_available_authentication_devices, _get_key_storage_folder_path
from wacryptolib.exceptions import KeyStorageAlreadyExists
from waguilib.widgets.popups import display_info_toast, close_current_dialog, dialog_with_close_button

Builder.load_file(str(Path(__file__).parent / 'authentication_device_store.kv'))


class AuthenticationDeviceStoreScreen(Screen):

    filesystem_key_storage_pool = ObjectProperty(None)

    def __init__(self, *args, **kwargs):
        self.selected_authentication_device_uids = []  # List of STRINGS
        self.register_event_type('on_selected_authentication_devices_changed')
        super().__init__(*args, **kwargs)

    def on_selected_authentication_devices_changed(self, *args):
         pass
         #print("I am dispatched on_selected_authentication_devices_changed", args)

    def import_keys(self):
        """
        loop through the “authentication_devices” present,
        and for those who are initialize, copy (with different KeyStorage for each folder)
        their content in a <KEYS_ROOT> / <device_uid> / folder (taking the device_uid from metadata.json)
        """
        # list_devices = list_available_authentication_devices()
        # print(list_devices)
        # for index, authentication_device in enumerate(list_devices):
        #print(">>>>>>>>>> import_keys started")
        authentication_devices = list_available_authentication_devices()
        #print("DETECTED AUTH DEVICES", authentication_devices)

        if not authentication_devices:
            msg = tr._("No connected authentication devices found")
        else:

            authentication_devices_initialized = [x for x in authentication_devices if x["is_initialized"]]

            if not authentication_devices_initialized:
                msg = tr._("No initialized authentication devices found")
            else:
                device_uids = []

                for authentication_device in authentication_devices_initialized:
                    #print(">>>>>>>>>> importing,", authentication_device)
                    key_storage_folder_path = _get_key_storage_folder_path(authentication_device)  # FIXME make it public?
                    try:
                        self.filesystem_key_storage_pool.import_key_storage_from_folder(key_storage_folder_path)
                    except KeyStorageAlreadyExists:
                        pass  # We tried anyway, since some "update" mechanics might be setup one day
                    device_uids.append(authentication_device["metadata"]["device_uid"])

                msg = "%d authentication device(s) updated" % len(device_uids)

                # Autoselect freshly imported keys
                self._change_authenticator_selection_status(device_uids=device_uids, is_selected=True)

        display_info_toast(msg)

        # update the display of authentication_device saved in the local folder .keys_storage_ward
        self.list_imported_key_devices(display_toast=False)

    def delete_keys(self):

        # FIXME add confirmation dialog!!

        device_uids = self.selected_authentication_device_uids

        if not device_uids:
            msg = "Please select authentication devices to delete"
        else:
            # TODO move this to WACRYPTOLIB!
            for device_uid in device_uids:
                path = self.filesystem_key_storage_pool._get_imported_key_storage_path(device_uid)
                try:
                    shutil.rmtree(path)
                except OSError as exc:
                    logging.error("Failed deletion of imported authentication device %s: %r", device_uid, exc)
            msg = "Selected imported authentication devices were deleted"

            self._change_authenticator_selection_status(device_uids=device_uids, is_selected=False)  # Update selection list

        display_info_toast(msg)

        self.list_imported_key_devices(display_toast=False)


    def list_imported_key_devices(self, display_toast=True):
        """
        loop through the KEYS_ROOT / files, and read their metadata.json,
        to display in the interface their USER and the start of their UUID

        KEYS_ROOT = “~/.keys_storage_ward/”
        """
        #print(">> we refresh auth devices panel")
        Keys_page_ids = self.ids  # FIXME rename this

        Keys_page_ids.imported_authenticator_list.clear_widgets()  # FIXME naming
        Keys_page_ids.imported_authenticator_list.do_layout()  # Prevents bug with "not found" message position

        key_storage_metadata = self.filesystem_key_storage_pool.list_imported_key_storage_metadata()

        if not key_storage_metadata:
            self.display_message_no_device_found()
            return

        #self.chbx_lbls = {}  # FIXME: lbls ?
        #self.btn_lbls = {}  # FIXME: lbls ?

        for (index, (device_uid, metadata)) in enumerate(sorted(key_storage_metadata.items()), start=1):
            uuid_suffix = str(device_uid).split("-")[-1]
            #print("COMPARING", str(device_uid), self.selected_authentication_device_uids)
            # my_check_box = CheckBox(
            #     active=(str(device_uid) in self.selected_authentication_device_uids),
            #     size_hint=(0.15, None),
            #     on_release=self.check_box_authentication_device_checked,
            #     height=40,
            # )
            # my_check_btn = Button(
            #     text="Key n°%s, User %s, Uid %s" % (index, metadata["user"], uuid_suffix),
            #     size_hint=(0.85, None),
            #     #background_color=(0, 1, 1, 0.1),
            #     on_release=functools.partial(self.info_keys_stored, device_uid=device_uid, user=metadata["user"]),
            #     height=40,
            # )
            # self.chbx_lbls[my_check_box] = str(device_uid)
            # self.btn_lbls[my_check_btn] = str(device_uid)
           # device_row = BoxLayout(
            #    orientation="horizontal",
                #pos_hint={"center": 1, "top": 1},
                #padding=[20, 0],
           #)
            authenticator_label = tr._("Key n°%s, User %s, Uid %s") % (index, metadata["user"], uuid_suffix)
            authenticator_entry = Factory.WASelectableListItemEntry(text=authenticator_label)  # FIXME RENAME THIS

            selection_checkbox = authenticator_entry.ids.selection_checkbox
            #print(">>>>>>>>selection_checkbox", selection_checkbox)
            selection_checkbox.active = str(device_uid) in self.selected_authentication_device_uids
            def selection_callback(widget, value, device_uid=device_uid):  # Force device_uid save here, else scope bug
                self.check_box_authentication_device_checked(device_uid=device_uid, is_selected=value)
            selection_checkbox.bind(active=selection_callback)

            information_icon = authenticator_entry.ids.information_icon
            def information_callback(widget, device_uid=device_uid, metadata=metadata):  # Force device_uid save here, else scope bug
                self.info_keys_stored(device_uid=device_uid, user=metadata["user"])
            information_icon.bind(on_press=information_callback)

            Keys_page_ids.imported_authenticator_list.add_widget(authenticator_entry)
            #Keys_page_ids.device_table.add_widget(my_check_btn)
            #Keys_page_ids.device_table.add_widget(device_row)

        if display_toast:
            display_info_toast(tr._("Refreshed imported authenticators"))
        """
                file_metadata = Path(dir_key_sorage).joinpath(".metadata.json")
                if file_metadata.exists():

                    metadata = load_from_json_file(file_metadata)
                    device_uid = str(metadata["device_uid"])
                    uuid = device_uid.split("-")
                    start_of_uuid = uuid[0].lstrip()
                    start_of_UUID = start_of_uuid.rstrip()
                    my_check_box = CheckBox(#start
                        active=False,
                        size_hint=(0.2, 0.2),
                        on_release=self.check_box_authentication_device_checked,
                    )
                    my_check_btn = Button(
                        text=" key N°:  %s        User:  %s      |      UUID device:  %s "
                        % ((str(index + 1)), str(metadata["user"]), start_of_UUID),
                        size_hint=(0.8, 0.2),
                        background_color=(1, 1, 1, 0.01),
                        on_press=self.info_keys_stored,
                    )
                    self.chbx_lbls[my_check_box] = str(metadata["device_uid"])
                    self.btn_lbls[my_check_btn] = str(metadata["device_uid"])
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
        Display_layout.ids.inner_label.text = tr._("No imported autentication device found")
        keys_page_ids = self.ids
        keys_page_ids.imported_authenticator_list.add_widget(Display_layout)

    def check_box_authentication_device_checked(self, device_uid: uuid.UUID, is_selected: bool):
        self._change_authenticator_selection_status(device_uids=[device_uid], is_selected=is_selected,)

    def _change_authenticator_selection_status(self, device_uids: list, is_selected: bool):
        for device_uid in device_uids:
            device_uid_str = str(device_uid)
            if not is_selected and device_uid_str in self.selected_authentication_device_uids:
                self.selected_authentication_device_uids.remove(device_uid_str)
            elif is_selected and device_uid_str not in self.selected_authentication_device_uids:
                self.selected_authentication_device_uids.append(device_uid_str)
        self.dispatch('on_selected_authentication_devices_changed', self.selected_authentication_device_uids)
        #print("self.selected_authentication_device_uids", self.selected_authentication_device_uids)

    def info_keys_stored(self, device_uid, user):

        """
        display the information of the keys stored in the selected usb

        """
        imported_key_storage = self.filesystem_key_storage_pool.get_imported_key_storage(key_storage_uid=device_uid)
        keypair_identifiers = imported_key_storage.list_keypair_identifiers()

        message = ""
        for index, keypair_identifier in enumerate(keypair_identifiers, start=1):

            private_key_present_str = "Yes" if keypair_identifier["private_key_present"] else "No"
            uuid_suffix = str(keypair_identifier["keychain_uid"]).split("-")[-1]

            message += (
                " Key n° %s, Uid: ...%s, type: %s\n" #, has_private_key:    %s\n"
                % (
                    index,
                    uuid_suffix,
                    keypair_identifier["key_type"],
                    #private_key_present_str,
                )
                )
        self.open_dialog_display_keys_in_authentication_device(message, user=user)

    def open_dialog_display_keys_in_authentication_device(self, message, user):
        dialog_with_close_button(
            close_btn_label=tr._("Close"),
            title=tr._("Imported authentication device of user %s") % user,
            text=message,
        )

