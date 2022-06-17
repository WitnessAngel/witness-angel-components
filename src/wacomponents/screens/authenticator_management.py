from datetime import datetime
from enum import Enum, unique
from pathlib import Path
from textwrap import dedent

import shutil
from functools import partial
from kivy.clock import Clock
from kivy.factory import Factory
from kivy.lang import Builder
from kivy.logger import Logger as logger
from kivy.properties import ObjectProperty, StringProperty
from kivymd.uix.button import MDFlatButton
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.list import IconLeftWidget
from kivymd.uix.screen import Screen

from wacomponents.default_settings import INTERNAL_AUTHENTICATOR_DIR, EXTERNAL_APP_ROOT, EXTERNAL_EXPORTS_DIR, \
    strip_external_app_root_prefix
from wacomponents.i18n import tr
from wacomponents.system_permissions import request_external_storage_dirs_access
from wacomponents.utilities import convert_bytes_to_human_representation, shorten_uid
from wacomponents.widgets.layout_components import LanguageSwitcherScreenMixin
from wacomponents.widgets.popups import dialog_with_close_button, register_current_dialog, close_current_dialog, \
    help_text_popup, display_info_toast
from wacomponents.widgets.popups import safe_catch_unhandled_exception_and_display_popup
from wacryptolib.authdevice import list_available_authdevices
from wacryptolib.authenticator import is_authenticator_initialized
from wacryptolib.exceptions import KeyLoadingError, SchemaValidationError
from wacryptolib.keygen import load_asymmetric_key_from_pem_bytestring
from wacryptolib.keystore import FilesystemKeystore, load_keystore_metadata, _get_keystore_metadata_file_path

Builder.load_file(str(Path(__file__).parent / 'authenticator_management.kv'))


@unique
class AuthenticatorType(Enum):
   USER_PROFILE = 1
   CUSTOM_FOLDER = 2
   USB_DEVICE = 3


class FolderKeyStoreListItem(Factory.ThinTwoLineAvatarIconListItem):
    ''' FAILED attempt at fixing button position on this item
    def __init__(self):
        super().__init__()
        #print(">>>>>>>>>>>>>>", self._EventDispatcher__event_stack)
        #print(">>>>>>>>>>>>>>>>>>", self.size, self.__class__.__mro__, "\n", self.__class__, "\n", self.__dict__, hex(id(self)))
        ##Clock.schedule_once(lambda x: self.dispatch('on_focus'))
        def force_reset(*args):
            prop = self.property('size')
            # dispatch this property on the button instance
            prop.dispatch(self)
        Clock.schedule_once(force_reset, timeout=1)
    '''

class AuthenticatorSelectorScreen(LanguageSwitcherScreenMixin, Screen):

    AUTHENTICATOR_ARCHIVE_FORMAT = "zip"

    AUTHENTICATOR_INITIALIZATION_STATUS_ICONS = {
        True: "check-circle-outline",  # or check-bold
        False: "checkbox-blank-off-outline",
        None: "file-question-outline",
    }

    selected_authenticator_dir = ObjectProperty(None, allownone=True) # Path of selected authenticator entry

    selected_custom_folder_path = ObjectProperty(None, allownone=True)  # Custom folder selected for FolderKeyStoreListItem entry

    authenticator_status = ObjectProperty(None, allownone=True)
    authenticator_status_message = StringProperty("")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        Clock.schedule_once(lambda *args, **kwargs: self.refresh_authenticator_list())  # "on_pre_enter" is not called for initial screen
        self._folder_chooser = MDFileManager(
            selector="folder",
            exit_manager=lambda x: close_current_dialog(),
            select_path=lambda x: (close_current_dialog(), self._folder_chooser_select_path(x)),
        )
        self._archive_chooser = MDFileManager(
            selector="file",
            ext=["." + self.AUTHENTICATOR_ARCHIVE_FORMAT],
            exit_manager=lambda x: close_current_dialog(),
            select_path=lambda x: (close_current_dialog(), self._import_authenticator_from_archive(x)),
        )

    def language_menu_select(self, lang_code):
        super().language_menu_select(lang_code)
        self.refresh_authenticator_list()  # Refresh translation of Drive etc.

    @safe_catch_unhandled_exception_and_display_popup
    def refresh_authenticator_list(self):

        try:
            authdevice_list = list_available_authdevices()
        except ModuleNotFoundError:  # probably on android, so no UDEV system
            authdevice_list = []

        authenticator_list_widget = self.ids.authenticator_list
        authenticator_list_widget.clear_widgets()

        authenticator_list_entries = []  # Pairs (widget, metadata)

        profile_authenticator_widget = Factory.UserKeyStoreListItem()
        authenticator_list_entries.append((profile_authenticator_widget, dict(authenticator_type=AuthenticatorType.USER_PROFILE)))

        folder_authenticator_widget = Factory.FolderKeyStoreListItem()
        folder_authenticator_widget.selected_path = self.selected_custom_folder_path
        self.bind(selected_custom_folder_path = folder_authenticator_widget.setter('selected_path'))
        folder_authenticator_widget.ids.open_folder_btn.bind(on_press=self.folder_chooser_open)  #
        authenticator_list_entries.append((folder_authenticator_widget, dict(authenticator_type=AuthenticatorType.CUSTOM_FOLDER)))

        for index, authdevice in enumerate(authdevice_list):

            filesystem_size = convert_bytes_to_human_representation(authdevice["filesystem_size"])
            filesystem = authdevice["filesystem_format"].upper()

            authenticator_widget = Factory.ThinTwoLineAvatarIconListItem(
                text=tr._("Drive: {drive} ({label})").format(drive=authdevice["partition_mountpoint"], label=authdevice["partition_label"] or tr._("no name")),
                secondary_text=tr._("Size: {size}, Filesystem: {filesystem}").format(size=filesystem_size, filesystem=filesystem),
            )
            authenticator_widget.add_widget(IconLeftWidget(icon="usb-flash-drive"))
            authenticator_list_entries.append((authenticator_widget, dict(authenticator_type=AuthenticatorType.USB_DEVICE, **authdevice)))

        for (authenticator_widget, authenticator_metadata) in authenticator_list_entries:
            authenticator_widget._authenticator_metadata = authenticator_metadata
            authenticator_widget._onrelease_callback = partial(self.display_authenticator_info, authenticator_metadata=authenticator_metadata)
            authenticator_widget.bind(on_release=authenticator_widget._onrelease_callback)
            authenticator_list_widget.add_widget(authenticator_widget)

        display_info_toast(tr._("Refreshed authenticator locations"))

        self.reselect_previously_selected_authenticator()  # Preserve previous selection across refreshes

    def _get_authenticator_dir_from_metadata(self, authenticator_metadata):
        authenticator_type = authenticator_metadata["authenticator_type"]
        if authenticator_type == AuthenticatorType.USER_PROFILE:
            authenticator_dir = INTERNAL_AUTHENTICATOR_DIR
        elif authenticator_type == AuthenticatorType.CUSTOM_FOLDER:
            authenticator_dir = self.selected_custom_folder_path
        else:
            assert authenticator_type == AuthenticatorType.USB_DEVICE
            authenticator_dir = authenticator_metadata["authenticator_dir"]
        return authenticator_dir

    def _folder_chooser_select_path(self, path, *args):
        self.selected_custom_folder_path = Path(path)
        authenticator_widget = self.ids.authenticator_list.children[-2]  # AUTOSELECT "custom folder" item
        authenticator_widget._onrelease_callback(authenticator_widget)

    def folder_chooser_open(self, widget, *args):
        if not request_external_storage_dirs_access():
            return
        file_manager_path = EXTERNAL_APP_ROOT
        previously_selected_custom_folder_path = self.selected_custom_folder_path
        if previously_selected_custom_folder_path and previously_selected_custom_folder_path.is_dir():
            file_manager_path = previously_selected_custom_folder_path
        self._folder_chooser.show(str(file_manager_path))  # Soon use .show_disks!!
        register_current_dialog(self._folder_chooser)

    def reselect_previously_selected_authenticator(self):
        previouslyselected_authenticator_dir = self.selected_authenticator_dir
        if previouslyselected_authenticator_dir:
            result = self._select_matching_authenticator_entry(previouslyselected_authenticator_dir)
            if not result:
                self.selected_authenticator_dir = None  # Extra security
                self._select_default_authenticator_entry()
        else:
            self._select_default_authenticator_entry()

    def _select_default_authenticator_entry(self):
        authenticator_widget = self.ids.authenticator_list.children[-1]  # ALWAYS EXISTS
        authenticator_widget._onrelease_callback(authenticator_widget)

    def _select_matching_authenticator_entry(self, authenticator_dir):
        authenticator_list_widget = self.ids.authenticator_list
        for authenticator_widget in authenticator_list_widget.children:  # Starts from bottom of list so!
            target_authenticator_dir = self._get_authenticator_dir_from_metadata(authenticator_widget._authenticator_metadata)
            if target_authenticator_dir == authenticator_dir:
                authenticator_widget._onrelease_callback(authenticator_widget)
                return True
        return False

    def _get_authenticator_status_message(self, authenticator_status):
        if authenticator_status is None:
            return tr._("No valid location selected")
        elif not authenticator_status:
            return tr._("Authenticator not initialized")
        else:
            return tr._("Authenticator initialized")

    @safe_catch_unhandled_exception_and_display_popup
    def display_authenticator_info(self, authenticator_widget, authenticator_metadata):

        authenticator_list_widget = self.ids.authenticator_list

        for child in authenticator_list_widget.children:
            assert hasattr(child, "opposite_colors"), child
            child.bg_color = authenticator_widget.theme_cls.bg_light
        authenticator_widget.bg_color = authenticator_widget.theme_cls.bg_darkest

        authenticator_info_text = ""
        authenticator_dir = self._get_authenticator_dir_from_metadata(authenticator_metadata)
        authenticator_dir_shortened = strip_external_app_root_prefix(authenticator_dir)

        if not authenticator_dir:
            authenticator_info_text = tr._("Please select an authenticator folder")
            authenticator_status = None

        elif not authenticator_dir.parent.exists():  # Parent folder only is enough!
            authenticator_info_text = tr._("Selected folder is invalid\nPath: %s" % authenticator_dir_shortened)
            authenticator_status = None

        elif not is_authenticator_initialized(authenticator_dir):
            authenticator_info_text = tr._("Path: %s") % authenticator_dir_shortened
            authenticator_status = False

        elif is_authenticator_initialized(authenticator_dir):

            try:
                authenticator_metadata = load_keystore_metadata(authenticator_dir)
            except SchemaValidationError as exc:
                authenticator_status = None
                authenticator_info_text = tr._("Invalid authenticator data in %s") % authenticator_dir
                logger.warning("Invalid authenticator data: %r", exc)

            else:
                authenticator_status = True
                _displayed_values = dict(
                    authenticator_dir=authenticator_dir_shortened,
                    keystore_uid=authenticator_metadata["keystore_uid"],
                    keystore_owner=authenticator_metadata["keystore_owner"],
                    keystore_passphrase_hint=authenticator_metadata["keystore_passphrase_hint"],  # FIXME might be missing because OPTIONAL!!!
                )

                authenticator_info_text = dedent(tr._("""\
                    Path: {authenticator_dir}
                    ID: {keystore_uid}
                    User: {keystore_owner}
                    Password hint: {keystore_passphrase_hint}
                """)).format(**_displayed_values)

        textarea = self.ids.authenticator_information
        textarea.text = authenticator_info_text

        self.selected_authenticator_dir = authenticator_dir  # Might be None
        self.authenticator_status = authenticator_status
        self.authenticator_status_message = self._get_authenticator_status_message(authenticator_status)


    def archive_chooser_open(self, *args):
        if not request_external_storage_dirs_access():
            return
        file_manager_path = EXTERNAL_EXPORTS_DIR
        self._archive_chooser.show(str(file_manager_path))  # Soon use .show_disks!!
        register_current_dialog(self._archive_chooser)

    @safe_catch_unhandled_exception_and_display_popup
    def _import_authenticator_from_archive(self, archive_path):

        archive_path = Path(archive_path)
        authenticator_dir = self.selected_authenticator_dir

        # BEWARE - might override target files!
        shutil.unpack_archive(archive_path, extract_dir=authenticator_dir, format=self.AUTHENTICATOR_ARCHIVE_FORMAT)

        dialog_with_close_button(
            title=tr._("Import successful"),
            text=tr._("Authenticator archive unpacked from %s, its integrity has not been checked though.") % archive_path.name,
            )

        self.refresh_authenticator_list()

    def show_authenticator_export_confirmation_dialog(self):
        dialog_with_close_button(
            close_btn_label=tr._("Cancel"),
            title=tr._("Export authenticator"),
            text=tr._("The exported archive should be kept in a secure place."),
            #size_hint=(0.8, 1),
            buttons=[MDFlatButton(text=tr._("Confirm"), on_release=lambda *args: (close_current_dialog(), self._export_authenticator_to_archive()))],
        )

    @safe_catch_unhandled_exception_and_display_popup
    def _export_authenticator_to_archive(self):
        authenticator_dir = self.selected_authenticator_dir

        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")

        # This loading is not supposed to fail, by construction
        authenticator_metadata = load_keystore_metadata(authenticator_dir)

        if not request_external_storage_dirs_access():
            return

        keystore_uid_shortened = shorten_uid(authenticator_metadata["keystore_uid"])
        EXTERNAL_EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        archive_path_base = EXTERNAL_EXPORTS_DIR.joinpath("authenticator_%s_%s" % (keystore_uid_shortened, timestamp))
        archive_path = shutil.make_archive(base_name=archive_path_base, format=self.AUTHENTICATOR_ARCHIVE_FORMAT,
                            root_dir=authenticator_dir)

        dialog_with_close_button(
            title=tr._("Export successful"),
            text=tr._("Authenticator archive exported to %s") % strip_external_app_root_prefix(archive_path),
            )

    def show_authenticator_destroy_confirmation_dialog(self):
        authenticator_dir = self.selected_authenticator_dir
        dialog_with_close_button(
            close_btn_label=tr._("Cancel"),
            title=tr._("Destroy authenticator"),
            text=tr._("Beware, this might make encrypted data using these keys impossible to decrypt."),
            #size_hint=(0.8, 1),
            buttons=[MDFlatButton(text=tr._("Confirm"), on_release=lambda *args: (close_current_dialog(), self._delete_authenticator_data(authenticator_dir)))],
        )

    @safe_catch_unhandled_exception_and_display_popup
    def _delete_authenticator_data(self, authenticator_dir):
        # FIXME protect against any OSERROR here!!
        # FIXME Move this operation to WACRYPTOLIB?
        metadata_file_path = _get_keystore_metadata_file_path(authenticator_dir)
        key_files = authenticator_dir.glob("*.pem")
        for filepath in [metadata_file_path] + list(key_files):
            try:
                filepath.unlink()  # TODO use missing_ok=True later
            except FileNotFoundError:
                pass
        dialog_with_close_button(
                title=tr._("Deletion is over"),
                text=tr._("All authentication data from folder %s has been removed.") % authenticator_dir,
            )
        self.refresh_authenticator_list()

    def show_checkup_dialog(self):
        authenticator_dir = self.selected_authenticator_dir
        dialog = dialog_with_close_button(
            auto_open_and_register=False,  # Important, we customize before
            close_btn_label=tr._("Cancel"),
            title=tr._("Sanity check"),
            type="custom",
            content_cls=Factory.AuthenticatorTesterContent(),
            buttons=[MDFlatButton(text=tr._("Check"), on_release=lambda *args:  self._check_authenticator_integrity(dialog, authenticator_dir))],
        )
        def _set_focus_on_passphrase(*args):
            dialog.content_cls.ids.tester_passphrase.focus = True
        dialog.bind(on_open=_set_focus_on_passphrase)
        dialog.open()
        register_current_dialog(dialog)  # To handle BACK button here too

    @safe_catch_unhandled_exception_and_display_popup
    def _check_authenticator_integrity(self, dialog, authenticator_dir):
        keystore_passphrase = dialog.content_cls.ids.tester_passphrase.text
        close_current_dialog()
        result_dict = self._test_authenticator_passphrase(authenticator_dir=authenticator_dir, keystore_passphrase=keystore_passphrase)

        keypair_count= result_dict["keypair_count"]
        missing_private_keys = result_dict["missing_private_keys"]
        undecodable_private_keys = result_dict["undecodable_private_keys"]

        if keypair_count and not missing_private_keys and not undecodable_private_keys:
            result = tr._("Success")
            details = tr._("Keypairs successfully tested: %s") % keypair_count
        else:
            result = tr._("Failure")
            missing_private_keys_shortened = [shorten_uid(k) for k in missing_private_keys]
            undecodable_private_keys_shortened = [shorten_uid(k) for k in undecodable_private_keys]
            details = tr._("Keypairs tested: {keypair_count}\nMissing private keys: {missing_private_keys}\nWrong passphrase for keys:  {undecodable_private_keys}").format(
                    keypair_count=keypair_count,
                    missing_private_keys=(", ".join(missing_private_keys_shortened) or "-"),
                    undecodable_private_keys=", ".join(undecodable_private_keys_shortened) or "-")

        dialog_with_close_button(
            title=tr._("Checkup result: %s") % result,
            text=details,
            )

    def _test_authenticator_passphrase(self, authenticator_dir, keystore_passphrase):
        filesystem_keystore = FilesystemKeystore(authenticator_dir)

        missing_private_keys = []
        undecodable_private_keys = []

        keypair_identifiers = filesystem_keystore.list_keypair_identifiers()

        for key_information in keypair_identifiers:
            keychain_uid = key_information["keychain_uid"]
            key_algo = key_information["key_algo"]
            if not key_information["private_key_present"]:
                missing_private_keys.append(keychain_uid)
                continue
            private_key_pem = filesystem_keystore.get_private_key(keychain_uid=keychain_uid, key_algo=key_algo)
            try:
                key_obj = load_asymmetric_key_from_pem_bytestring(
                   key_pem=private_key_pem, key_algo=key_algo, passphrase=keystore_passphrase
                )
                assert key_obj, key_obj
            except KeyLoadingError:
                undecodable_private_keys.append(keychain_uid)

        return dict(keypair_count=len(keypair_identifiers),
                    missing_private_keys=missing_private_keys,
                    undecodable_private_keys=undecodable_private_keys)

    def showh_authenticator_publish_page(self):
        self.manager.current = "authenticator_synchronization_screen"
        #publish_authenticator_screen = self.manager.get_screen("authenticator_synchronization_screen")
        #publish_authenticator_screen.refresh_status()


    def display_help_popup(self):
        help_text = dedent(tr._("""\
        On this page, you can manage your authenticators, which are actually digital keychains identified by unique IDs.
        
        These keychains contain both public keys, which can be freely shared, and their corresponding private keys, protected by passphrases, which must be kept hidden.
        
        Authenticators can be stored in your user profile or in a custom folder, especially at the root of removable devices.
        
        You can initialize new authenticators from scratch, import/export them from/to ZIP archives, or check their integrity by providing their passphrases.
        
        Note that if you destroy an authenticator and all its exported ZIP archives, the WitnessAngel recordings which used it as a trusted third party might not be decryptable anymore (unless they used a shared secret with other trusted third parties).
        """))
        help_text_popup(
            title=tr._("Authenticator management page"),
            text=help_text,)
