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

from wacryptolib.authdevice import list_available_authdevices, get_authenticator_dir_for_authdevice
from wacryptolib.exceptions import KeystoreAlreadyExists
from waguilib.widgets.popups import display_info_toast, close_current_dialog, dialog_with_close_button

Builder.load_file(str(Path(__file__).parent / 'authdevice_store.kv'))


class AuthdeviceStoreScreen(Screen):

    filesystem_keystore_pool = ObjectProperty(None)

    def __init__(self, *args, **kwargs):
        self.selected_authenticator_uids = []  # List of STRINGS
        self.register_event_type('on_selected_authdevices_changed')
        super().__init__(*args, **kwargs)

    def on_selected_authdevices_changed(self, *args):
         pass
         #print("I am dispatched on_selected_authdevices_changed", args)

    def import_keys(self):
        """
        loop through the “authdevices” present,
        and for those who are initialize, copy (with different Keystore for each folder)
        their content in a <KEYS_ROOT> / <authenticator_uid> / folder (taking the authenticator_uid from metadata.json)
        """
        # list_devices = list_available_authdevices()
        # print(list_devices)
        # for index, authdevice in enumerate(list_devices):
        #print(">>>>>>>>>> import_keys started")
        authdevices = list_available_authdevices()
        #print("DETECTED AUTH DEVICES", authdevices)

        if not authdevices:
            msg = tr._("No connected authentication devices found")
        else:

            authdevices_initialized = [x for x in authdevices if x["is_initialized"]]

            if not authdevices_initialized:
                msg = tr._("No initialized authentication devices found")
            else:
                authenticator_uids = []

                for authdevice in authdevices_initialized:
                    #print(">>>>>>>>>> importing,", authdevice)
                    keystore_folder_path = get_authenticator_dir_for_authdevice(authdevice)  # FIXME make it public?
                    try:
                        self.filesystem_keystore_pool.import_keystore_from_folder(keystore_folder_path)
                    except KeystoreAlreadyExists:
                        pass  # We tried anyway, since some "update" mechanics might be setup one day
                    authenticator_uids.append(authdevice["metadata"]["authenticator_uid"])

                msg = "%d authenticators imported" % len(authenticator_uids)

                # Autoselect freshly imported keys
                self._change_authenticator_selection_status(authenticator_uids=authenticator_uids, is_selected=True)

        display_info_toast(msg)

        # update the display of authdevice saved in the local folder .keys_storage_ward
        self.list_imported_key_devices(display_toast=False)

    def delete_keys(self):

        # FIXME add confirmation dialog!!

        authenticator_uids = self.selected_authenticator_uids

        if not authenticator_uids:
            msg = "Please select authentication devices to delete"
        else:
            # TODO move this to WACRYPTOLIB!
            for authenticator_uid in authenticator_uids:
                path = self.filesystem_keystore_pool._get_imported_keystore_dir(authenticator_uid)
                try:
                    shutil.rmtree(path)
                except OSError as exc:
                    logging.error("Failed deletion of imported authentication device %s: %r", authenticator_uid, exc)
            msg = "Selected imported authentication devices were deleted"

            self._change_authenticator_selection_status(authenticator_uids=authenticator_uids, is_selected=False)  # Update selection list

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

        keystore_metadata = self.filesystem_keystore_pool.get_imported_keystore_metadata()

        if not keystore_metadata:
            self.display_message_no_device_found()
            return

        #self.chbx_lbls = {}  # FIXME: lbls ?
        #self.btn_lbls = {}  # FIXME: lbls ?

        for (index, (authenticator_uid, metadata)) in enumerate(sorted(keystore_metadata.items()), start=1):
            uuid_suffix = str(authenticator_uid).split("-")[-1]
            #print("COMPARING", str(authenticator_uid), self.selected_authenticator_uids)
            # my_check_box = CheckBox(
            #     active=(str(authenticator_uid) in self.selected_authenticator_uids),
            #     size_hint=(0.15, None),
            #     on_release=self.check_box_authdevice_checked,
            #     height=40,
            # )
            # my_check_btn = Button(
            #     text="Key n°%s, User %s, Uid %s" % (index, metadata["user"], uuid_suffix),
            #     size_hint=(0.85, None),
            #     #background_color=(0, 1, 1, 0.1),
            #     on_release=functools.partial(self.info_keys_stored, authenticator_uid=authenticator_uid, user=metadata["user"]),
            #     height=40,
            # )
            # self.chbx_lbls[my_check_box] = str(authenticator_uid)
            # self.btn_lbls[my_check_btn] = str(authenticator_uid)
           # device_row = BoxLayout(
            #    orientation="horizontal",
                #pos_hint={"center": 1, "top": 1},
                #padding=[20, 0],
           #)
            authenticator_label = tr._("User {user} - Uid {uid}").format(user=metadata["user"], uid=uuid_suffix)
            authenticator_entry = Factory.WASelectableListItemEntry(text=authenticator_label)  # FIXME RENAME THIS

            selection_checkbox = authenticator_entry.ids.selection_checkbox
            #print(">>>>>>>>selection_checkbox", selection_checkbox)
            selection_checkbox.active = str(authenticator_uid) in self.selected_authenticator_uids
            def selection_callback(widget, value, authenticator_uid=authenticator_uid):  # Force authenticator_uid save here, else scope bug
                self.check_box_authdevice_checked(authenticator_uid=authenticator_uid, is_selected=value)
            selection_checkbox.bind(active=selection_callback)

            information_icon = authenticator_entry.ids.information_icon
            def information_callback(widget, authenticator_uid=authenticator_uid, metadata=metadata):  # Force authenticator_uid save here, else scope bug
                self.info_keys_stored(authenticator_uid=authenticator_uid, user=metadata["user"])
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
                    authenticator_uid = str(metadata["authenticator_uid"])
                    uuid = authenticator_uid.split("-")
                    start_of_uuid = uuid[0].lstrip()
                    start_of_UUID = start_of_uuid.rstrip()
                    my_check_box = CheckBox(#start
                        active=False,
                        size_hint=(0.2, 0.2),
                        on_release=self.check_box_authdevice_checked,
                    )
                    my_check_btn = Button(
                        text=" key N°:  %s        User:  %s      |      UUID device:  %s "
                        % ((str(index + 1)), str(metadata["user"]), start_of_UUID),
                        size_hint=(0.8, 0.2),
                        background_color=(1, 1, 1, 0.01),
                        on_press=self.info_keys_stored,
                    )
                    self.chbx_lbls[my_check_box] = str(metadata["authenticator_uid"])
                    self.btn_lbls[my_check_btn] = str(metadata["authenticator_uid"])
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

    def check_box_authdevice_checked(self, authenticator_uid: uuid.UUID, is_selected: bool):
        self._change_authenticator_selection_status(authenticator_uids=[authenticator_uid], is_selected=is_selected,)

    def _change_authenticator_selection_status(self, authenticator_uids: list, is_selected: bool):
        for authenticator_uid in authenticator_uids:
            authenticator_uid_str = str(authenticator_uid)
            if not is_selected and authenticator_uid_str in self.selected_authenticator_uids:
                self.selected_authenticator_uids.remove(authenticator_uid_str)
            elif is_selected and authenticator_uid_str not in self.selected_authenticator_uids:
                self.selected_authenticator_uids.append(authenticator_uid_str)
        self.dispatch('on_selected_authdevices_changed', self.selected_authenticator_uids)
        #print("self.selected_authenticator_uids", self.selected_authenticator_uids)

    def info_keys_stored(self, authenticator_uid, user):

        """
        display the information of the keys stored in the selected usb

        """
        imported_keystore = self.filesystem_keystore_pool.get_imported_keystore(keystore_uid=authenticator_uid)
        keypair_identifiers = imported_keystore.list_keypair_identifiers()

        message = ""
        for index, keypair_identifier in enumerate(keypair_identifiers, start=1):

            private_key_present_str = "Yes" if keypair_identifier["private_key_present"] else "No"
            uuid_suffix = str(keypair_identifier["keychain_uid"]).split("-")[-1]

            message += (
                " Key n° %s, Uid: ...%s, type: %s\n" #, has_private_key:    %s\n"
                % (
                    index,
                    uuid_suffix,
                    keypair_identifier["key_algo"],
                    #private_key_present_str,
                )
                )
        self.open_dialog_display_keys_in_authdevice(message, user=user)

    def open_dialog_display_keys_in_authdevice(self, message, user):
        dialog_with_close_button(
            close_btn_label=tr._("Close"),
            title=tr._("Key Guardian %s") % user,
            text=message,
        )

