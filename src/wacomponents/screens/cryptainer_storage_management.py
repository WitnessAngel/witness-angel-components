
import logging
from pathlib import Path

from kivy.clock import Clock
from kivy.factory import Factory
from kivy.lang import Builder
from kivy.properties import ObjectProperty, ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivymd.uix.button import MDFlatButton
from kivymd.uix.snackbar import Snackbar

from wacomponents.default_settings import EXTERNAL_EXPORTS_DIR
from wacomponents.i18n import tr
from wacomponents.logging.handlers import safe_catch_unhandled_exception
from wacomponents.screens.base import WAScreenName, WAScreenBase
from wacomponents.utilities import (
    format_cryptainer_label,
    format_authenticator_label,
    SPACE,
    COLON,
    LINEBREAK,
    convert_bytes_to_human_representation,
)
from wacomponents.widgets.layout_components import build_fallback_information_box
from wacomponents.widgets.popups import (
    close_current_dialog,
    dialog_with_close_button,
    display_info_toast,
    safe_catch_unhandled_exception_and_display_popup,
)
from wacryptolib.cryptainer import gather_trustee_dependencies

Builder.load_file(str(Path(__file__).parent / "cryptainer_storage_management.kv"))


logger = logging.getLogger(__name__)


class PassphrasesDialogContent(BoxLayout):
    pass


class CryptainerStorageManagementScreen(WAScreenBase):

    #: The container storage managed by this Screen, might be None if unset
    filesystem_cryptainer_storage = ObjectProperty(None, allownone=True)

    selected_cryptainer_names = ListProperty(None, allownone=True)

    available_cryptainer_names = ObjectProperty(None, allownone=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.selected_cryptainer_names = []

    def _refresh_recycle_view(self):
        Clock.schedule_once(lambda x: self.ids.cryptainer_table.refresh_from_data())

    def select_all_cryptainers(self):
        del self.selected_cryptainer_names[:]
        self.selected_cryptainer_names.extend(self.available_cryptainer_names)
        #print(">> WE FILLED selected_unique_identifiers", self.selected_unique_identifiers)
        self._refresh_recycle_view()

    def deselect_all_cryptainers(self):
        del self.selected_cryptainer_names[:]
        #print(">> WE EMPTIED selected_unique_identifiers", self.selected_unique_identifiers)))
        self._refresh_recycle_view()

    @safe_catch_unhandled_exception_and_display_popup
    def refresh_cryptainer_list(self):
        self._refresh_cryptainer_list()

    def _refresh_cryptainer_list(self):

        cryptainers_page_ids = self.ids

        if self.filesystem_cryptainer_storage is None:
            fallback_info_box = build_fallback_information_box("\n\n" + tr._("Container storage is invalid"))
            cryptainers_page_ids.cryptainer_table.add_widget(fallback_info_box)
            return

        sorted_cryptainer_names = list(self.filesystem_cryptainer_storage.list_cryptainer_names(as_sorted_list=True))
        self.available_cryptainer_names = sorted_cryptainer_names

        # Cleanup selected cryptainers
        _still_valid_selected_cryptainer_names = [
            x for x in self.selected_cryptainer_names
            if x in sorted_cryptainer_names]
        del self.selected_cryptainer_names[:]
        self.selected_cryptainer_names.extend(_still_valid_selected_cryptainer_names)

        data = []
        for cryptainer_idx, cryptainer_name in enumerate(reversed(self.available_cryptainer_names)):

            cryptainer_label = format_cryptainer_label(cryptainer_name=cryptainer_name)
            try:
                cryptainer_size_bytes = self.filesystem_cryptainer_storage._get_cryptainer_size(cryptainer_name)
            except FileNotFoundError:
                cryptainer_size_bytes = None  # Probably deleted concurrently

            cryptainer_entry_label = tr._("N°") + SPACE + str(cryptainer_idx) + COLON() + cryptainer_label
            if cryptainer_size_bytes is not None:
                cryptainer_entry_label += " (%s)" % convert_bytes_to_human_representation(cryptainer_size_bytes)
            else:
                cryptainer_entry_label += " (%s)" % tr._("missing")

            data.append({"text": cryptainer_entry_label,
                         "unique_identifier": cryptainer_name,
                         "information_callback": self.show_cryptainer_details,
                         "selection_callback": self.handle_cryptainer_selection,
                         "selected_unique_identifiers": self.selected_cryptainer_names})

        cryptainers_page_ids.cryptainer_table.data = data
        self._refresh_recycle_view()

    def handle_cryptainer_selection(self, cryptainer_name, checkbox, value):
        #print('The checkbox', cryptainer_name, "is active=", value, 'and', checkbox.state, 'state')
        if value:
            if cryptainer_name not in self.selected_cryptainer_names:
                self.selected_cryptainer_names.append(cryptainer_name)
        else:
            if cryptainer_name in self.selected_cryptainer_names:
                self.selected_cryptainer_names.remove(cryptainer_name)

    def show_cryptainer_details(self, cryptainer_name):
        """
        Display the contents of container
        """

        logger.warning("Showing details for cryptainer %s", cryptainer_name)

        assert self.filesystem_cryptainer_storage, self.filesystem_cryptainer_storage  # By construction...
        cryptainer_label = ""

        try:
            cryptainer = self.filesystem_cryptainer_storage.load_cryptainer_from_storage(cryptainer_name)
            all_dependencies = gather_trustee_dependencies([cryptainer])
            interesting_dependencies = [d[0] for d in list(all_dependencies["encryption"].values())]
            interesting_dependencies.sort(key=lambda x: x["keystore_owner"].lower())  # Sort by pretty name
        except Exception as exc:
            message = repr(exc)[:800]

        else:

            message = tr._("Container ID") + COLON() + str(cryptainer["cryptainer_uid"]) + 2 * LINEBREAK

            message += tr._("Key Guardians used") + COLON() + LINEBREAK * 2
            for index, key_guardian_used in enumerate(interesting_dependencies, start=1):
                key_guardian_label = format_authenticator_label(
                    authenticator_owner=key_guardian_used["keystore_owner"],
                    keystore_uid=key_guardian_used["keystore_uid"],
                    trustee_type=key_guardian_used["trustee_type"],
                )

                message += tr._("N°") + SPACE + str(index) + COLON() + key_guardian_label + LINEBREAK

            cryptainer_label = str(cryptainer_name)  # It's a Path object

        self._open_cryptainer_details_dialog(message, cryptainer_label=cryptainer_label)

    def _open_cryptainer_details_dialog(self, message, cryptainer_label):
        dialog_with_close_button(close_btn_label=tr._("Close"), title=cryptainer_label, text=message)

    def open_cryptainer_deletion_dialog(self):

        selected_cryptainer_names = self.selected_cryptainer_names
        if not selected_cryptainer_names:
            msg = tr._("Please select containers to delete")
            display_info_toast(msg)
            return

        message = tr._("Are you sure you want to delete %s container(s)?") % len(selected_cryptainer_names)

        dialog_with_close_button(
            close_btn_label=tr._("Cancel"),
            title=tr._("Container deletion confirmation"),
            text=message,
            buttons=[
                MDFlatButton(
                    text=tr._("Confirm deletion"),
                    on_release=lambda *args: (
                        close_current_dialog(),
                        self.delete_cryptainers(cryptainer_names=selected_cryptainer_names),
                    ),
                )
            ],
        )

    def delete_cryptainers(self, cryptainer_names):
        logger.info("Deleting cryptainers %s", cryptainer_names)

        assert self.filesystem_cryptainer_storage, self.filesystem_cryptainer_storage  # By construction...
        for cryptainer_name in cryptainer_names:
            try:
                self.filesystem_cryptainer_storage.delete_cryptainer(cryptainer_name)
            except FileNotFoundError:
                pass  # File has probably been purged already

        self.refresh_cryptainer_list()

    def launch_cryptainer_decryption(self):
        selected_cryptainer_names = self.selected_cryptainer_names

        if not selected_cryptainer_names:
            msg = tr._("Please select containers to decrypt")
            display_info_toast(msg)
            return

        # print(">>>>>> selected_cryptainer_names in _launch_cryptainer_decryption()", selected_cryptainer_names)
        cryptainer_decryption_screen_name = WAScreenName.cryptainer_decryption_process
        cryptainer_decryption_screen = self.manager.get_screen(cryptainer_decryption_screen_name)
        cryptainer_decryption_screen.selected_cryptainer_names = (
            selected_cryptainer_names
        )  # FIXME change the system of propagation of this ?
        self.manager.current = cryptainer_decryption_screen_name