import functools
import pprint
from pathlib import Path

from kivy.factory import Factory
from kivy.lang import Builder
from kivy.uix.recycleview import RecycleView
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.properties import StringProperty, ListProperty, ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivymd.uix.button import MDFlatButton
from kivymd.uix.screen import Screen
from kivymd.uix.snackbar import Snackbar
from functools import partial


from wacomponents.i18n import tr
from wacomponents.default_settings import EXTERNAL_EXPORTS_DIR
from wacomponents.logging.handlers import safe_catch_unhandled_exception

from wacryptolib.cryptainer import gather_trustee_dependencies
from wacomponents.widgets.popups import close_current_dialog, dialog_with_close_button

Builder.load_file(str(Path(__file__).parent / 'cryptainer_storage_management.kv'))


class PassphrasesDialogContent(BoxLayout):
    pass


class CryptainerStoreScreen(Screen):
    #: The container storage managed by this Screen, might be None if unset
    filesystem_cryptainer_storage = ObjectProperty(None, allownone=True)
    cryptainer_names_to_be_loaded = ObjectProperty(None, allownone=True)
    cryptainer_loading_schedule = ObjectProperty(None, allownone=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # print("CREATED CryptainerStoreScreen")

    def cancel_cryptainer_loading(self, *args):
        if self.cryptainer_loading_schedule:
            self.cryptainer_loading_schedule.cancel()
            self.cryptainer_loading_schedule = None
            self.cryptainer_names_to_be_loaded = []


    def _get_selected_cryptainer_names(self):
        cryptainer_names = []
        for cryptainer_entry in self.ids.cryptainer_table.children:
            if getattr(cryptainer_entry, "selected", None):  # Beware of WABigInformationBox
                assert cryptainer_entry.unique_identifier, cryptainer_entry.unique_identifier
                cryptainer_names.append(cryptainer_entry.unique_identifier)
        # print(">>>>> extract_selected_cryptainer_names", container_names)
        return cryptainer_names

    @safe_catch_unhandled_exception
    def get_detected_cryptainer(self):
        self._get_detected_cryptainer()

    def _get_detected_cryptainer(self):
        self.cancel_cryptainer_loading()

        # FIXME use RecycleView instead for performance!!
        # https://stackoverflow.com/questions/70333878/kivymd-recycleview-has-low-fps-lags

        cryptainers_page_ids = self.ids

        # self.root.ids.screen_manager.get_screen(
        #    "Container_management"
        # ).ids
        cryptainers_page_ids.cryptainer_table.clear_widgets()
        cryptainers_page_ids.cryptainer_table.do_layout()  # Prevents bug with "not found" message position

        # print(">>>>>>>>>>>>>self.filesystem_cryptainer_storage, ", self.filesystem_cryptainer_storage)
        if self.filesystem_cryptainer_storage is None:
            display_layout = Factory.WABigInformationBox()
            display_layout.ids.inner_label.text = tr._("Container storage is invalid")  # FIXME simplify this
            cryptainers_page_ids.cryptainer_table.add_widget(display_layout)
            return

        sorted_cryptainers = list(enumerate(self.filesystem_cryptainer_storage.list_cryptainer_names(as_sorted_list=True), start=1))
        self.cryptainer_names_to_be_loaded = list(reversed(sorted_cryptainers))

        if not self.cryptainer_names_to_be_loaded:
            display_layout = Factory.WABigInformationBox()
            display_layout.ids.inner_label.text = tr._("No containers found")
            cryptainers_page_ids.cryptainer_table.add_widget(display_layout)
            return

        self.check_box_cryptainer_uuid_dict = {}
        self.btn_cryptainer_uuid_dict = {}

        self.cryptainer_checkboxes = []

        assert not self.cryptainer_loading_schedule
        self.cryptainer_loading_schedule = Clock.schedule_interval(partial(self.load_next_scheduled_cryptainer), 0.02)

    def load_next_scheduled_cryptainer(self, *args):
        if self.cryptainer_names_to_be_loaded:
            cryptainer_idx, cryptainer_name = self.cryptainer_names_to_be_loaded.pop()
            self._load_cryptainer(index=cryptainer_idx, cryptainer_name=cryptainer_name)
        else:
            self.cryptainer_loading_schedule.cancel()

    def _load_cryptainer(self, index, cryptainer_name):
        cryptainer_label = tr._("N° {index}: {cryptainer_name}").format(index=index, cryptainer_name=cryptainer_name)
        cryptainer_entry = Factory.WASelectableListItemEntry(text=cryptainer_label)  # FIXME RENAME THIS
        cryptainer_entry.unique_identifier = cryptainer_name

        def information_callback(widget, cryptainer_name=cryptainer_name):  # Force keystore_uid save here, else scope bug
            self.show_cryptainer_details(cryptainer_name=cryptainer_name)

        information_icon = cryptainer_entry.ids.information_icon
        information_icon.bind(on_press=information_callback)

        self.ids.cryptainer_table.add_widget(cryptainer_entry)
        print("ADDED CRYPTAINER", cryptainer_name)

    def get_selected_cryptainer_names(self):

        cryptainers_page_ids = self.ids

        cryptainer_names = []

        checkboxes = list(reversed(cryptainers_page_ids.cryptainer_table.children))[::2]

        for checkbox in checkboxes:
            if checkbox.active:
                cryptainer_names.append(checkbox._cryptainer_name)

        # print("container_names", container_names)
        return cryptainer_names

    def show_cryptainer_details(self, cryptainer_name):
        """
        Display the contents of container
        """
        assert self.filesystem_cryptainer_storage, self.filesystem_cryptainer_storage  # By construction...
        try:
            cryptainer = self.filesystem_cryptainer_storage.load_cryptainer_from_storage(cryptainer_name)
            all_dependencies = gather_trustee_dependencies([cryptainer])
            interesting_dependencies = [d[0] for d in list(all_dependencies["encryption"].values())]
            cryptainer_repr = "\n".join(str(trustee) for trustee in interesting_dependencies)
            # container_repr = pprint.pformat(interesting_dependencies, indent=2)[:800]  # LIMIT else pygame.error: Width or height is too large
        except Exception as exc:
            cryptainer_repr = repr(exc)

        cryptainer_repr = tr._("Key Guardians used:") + "\n\n" + cryptainer_repr

        self.open_cryptainer_details_dialog(cryptainer_repr, info_cryptainer=cryptainer_name)

    def open_cryptainer_details_dialog(self, message, info_cryptainer):
        dialog_with_close_button(
            close_btn_label=tr._("Close"),
            title=str(info_cryptainer),
            text=message,
        )
        '''
        self.dialog = MDDialog(
            title=str(info_cryptainer),
            text=message,
            size_hint=(0.8, 1),
            buttons=[MDFlatButton(text=tr._("Close"), on_release=lambda *args: close_current_dialog())],
        )
        self.dialog.open()
        '''

    def open_cryptainer_deletion_dialog(self):

        cryptainer_names = self._get_selected_cryptainer_names()
        if not cryptainer_names:
            return

        message = "Are you sure you want to delete %s container(s)?" % len(cryptainer_names)
        """
        self.list_chbx_active = []
        for chbx in self.check_box_cryptainer_uuid_dict:
            if chbx.active:
                self.list_chbx_active.append(chbx)

        count_cryptainer_checked =len(self.list_chbx_active)
        if count_cryptainer_checked == 1:
            messge = " do you want to delete these container?"
        elif count_cryptainer_checked > 1:
            messge = (
                " do you want to delete these %d containers"
                % count_cryptainer_checked
            )
        """
        dialog_with_close_button(
            close_btn_label=tr._("Cancel"),
            title=tr._("Container deletion confirmation"),
            text=message,
            buttons=[
                MDFlatButton(
                    text="Confirm deletion", on_release=lambda *args: (
                        close_current_dialog(), self.delete_cryptainers(cryptainer_names=cryptainer_names))
                ), ]
        )

    def delete_cryptainers(self, cryptainer_names):
        assert self.filesystem_cryptainer_storage, self.filesystem_cryptainer_storage  # By construction...
        for cryptainer_name in cryptainer_names:
            try:
                self.filesystem_cryptainer_storage.delete_cryptainer(cryptainer_name)
            except FileNotFoundError:
                pass  # File has probably been puregd already

        self.get_detected_cryptainer()  # FIXME rename

    def open_cryptainer_decryption_dialog(self):

        cryptainer_names = self._get_selected_cryptainer_names()
        if not cryptainer_names:
            return

        message = "Decrypt %s container(s)?" % len(cryptainer_names)

        """
        self.list_chbx_active = []
        for chbx in self.check_box_cryptainer_uuid_dict:
            if chbx.active:
                self.list_chbx_active.append(chbx)

        count_cryptainer_checked = len(self.list_chbx_active)

        if count_cryptainer_checked == 1:
            messge = " do you want to decipher these container?"
        elif count_cryptainer_checked > 1:
            messge = (
                    " Do you want to decipher these %d containers" % count_cryptainer_checked
            )
        """

        assert self.filesystem_cryptainer_storage, self.filesystem_cryptainer_storage  # By construction...
        filesystem_keystore_pool = self.filesystem_cryptainer_storage._keystore_pool  # FIXME add public getter
        keystore_metadata = filesystem_keystore_pool.get_imported_keystore_metadata()

        cryptainers = [self.filesystem_cryptainer_storage.load_cryptainer_from_storage(x) for x in cryptainer_names]
        dependencies = gather_trustee_dependencies(cryptainers)

        # BEWARE this only works for "authentication device" trustees!
        # TODO make this more generic with support for remote trustee!
        relevant_keystore_uids = [trustee[0]["keystore_uid"] for trustee in dependencies["encryption"].values()]

        relevant_keystore_metadata = sorted([y for (x, y) in keystore_metadata.items()
                                             if x in relevant_keystore_uids], key=lambda d: d["keystore_owner"])

        # print("--------------")
        # pprint.pprint(relevant_keystore_metadata)

        content_cls = PassphrasesDialogContent()

        # print(">>>>>>relevant_keystore_metadata", relevant_keystore_metadata)
        for metadata in relevant_keystore_metadata:
            hint_text = "Passphrase for user %s (hint: %s)" % (
                metadata["keystore_owner"], metadata["keystore_passphrase_hint"])
            _widget = TextInput(hint_text=hint_text)

            '''MDTextField(hint_text="S SSSSSSSS z z",
                              helper_text="Passphrase for user %s (hint: %s)" % (metadata["keystore_owner"], metadata["keystore_passphrase_hint"]),
                              helper_text_mode="on_focus",
                              **{                    "color_mode": 'custom',
                                                  "line_color_focus": (0.4, 0.5, 1, 1),
                                                  "mode": "fill",
                                                  "fill_color": (0.3, 0.3, 0.3, 0.4),
                                                  "current_hint_text_color": (0.1, 1, 0.2, 1)})'''
            content_cls.add_widget(_widget)

        dialog_with_close_button(
            close_btn_label=tr._("Cancel"),
            title=tr._("Container decryption confirmation"),
            type="custom",
            content_cls=content_cls,
            buttons=[
                MDFlatButton(
                    text="Launch decryption",
                    on_release=lambda *args: (close_current_dialog(),
                                              self.decipher_cryptainers(cryptainer_names=cryptainer_names,
                                                                        input_content_cls=content_cls)),
                ), ]
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

    def _launch_cryptainer_decryption(self):
        cryptainer_decryption_screen = self.manager.get_screen("CryptainerDecryption")
        selected_cryptainer_names = self._get_selected_cryptainer_names()
        # print(">>>>>> selected_cryptainer_names in _launch_cryptainer_decryption()", selected_cryptainer_names)
        cryptainer_decryption_screen.selected_cryptainer_names = selected_cryptainer_names
        self.manager.current = "CryptainerDecryption"

    @safe_catch_unhandled_exception
    def __UNUSED_offloaded_attempt_cryptainer_decryption(self, cryptainer_filepath):  # FIXME move out of here
        logger.info("Decryption requested for container %s", cryptainer_filepath)
        target_directory = EXTERNAL_EXPORTS_DIR.joinpath(
            os.path.basename(cryptainer_filepath)
        )
        target_directory.mkdir(
            exist_ok=True
        )  # Double exports would replace colliding files
        cryptainer = load_cryptainer_from_filesystem(cryptainer_filepath, include_payload_ciphertext=True)
        tarfile_bytes = decrypt_payload_from_cryptainer(
            cryptainer, keystore_pool=self._keystore_pool
        )
        tarfile_bytesio = io.BytesIO(tarfile_bytes)
        tarfile_obj = tarfile.open(
            mode="r", fileobj=tarfile_bytesio  # TODO add gzip support here one day
        )
        # Beware, as root on unix systems it would apply chown/chmod
        tarfile_obj.extractall(target_directory)
        logger.info(
            "Container content was successfully decrypted into folder %s",
            target_directory,
        )

    ##@osc.address_method("/attempt_cryptainer_decryption")
    @safe_catch_unhandled_exception
    def __UNUSED_attempt_cryptainer_decryption(self, cryptainer_filepath: str):  # FIXME move out of here
        cryptainer_filepath = Path(cryptainer_filepath)
        return self._offload_task(self._offloaded_attempt_cryptainer_decryption,
                                  cryptainer_filepath=cryptainer_filepath)

        """
        print("The written sentence is passphrase : %s" % input)
        containers = []
        for chbx in self.check_box_cryptainer_uuid_dict:
            if chbx.active:
                print(
                    "Decipher container | with ID_cryptainer %s",
                    self.check_box_cryptainer_uuid_dict[chbx],
                )
                container = load_cryptainer_from_filesystem(
                    container_filepath=Path(
                        ".container_storage_ward".format(self.check_box_cryptainer_uuid_dict[chbx][1])
                    )
                )
                containers.append(container)
        trustee_dependencies = gather_trustee_dependencies(containers=containers)

        decryption_authorizations = request_decryption_authorizations(
            trustee_dependencies=trustee_dependencies,
            keystore_pool=filesystem_keystore_pool,
            request_message="Need decryptions"
        )
        for container in containers:
            decrypt_payload_from_cryptainer(container=container)
            """
