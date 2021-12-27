import functools
import pprint
from pathlib import Path

from kivy.factory import Factory
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.config import Config
from kivy.properties import StringProperty, ListProperty, ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.screenmanager import ScreenManager
from kivy.uix.textinput import TextInput
from kivymd.uix.textfield import MDTextField
from kivymd.app import MDApp
from kivymd.theming import ThemableBehavior
from kivymd.uix.button import MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import OneLineIconListItem, MDList
from kivymd.uix.screen import Screen
from kivymd.uix.snackbar import Snackbar

from waguilib.i18n import tr
from waguilib.importable_settings import EXTERNAL_DATA_EXPORTS_DIR
from waguilib.logging.handlers import safe_catch_unhandled_exception

from wacryptolib.cryptainer import gather_escrow_dependencies
from waguilib.widgets.popups import close_current_dialog, dialog_with_close_button

Builder.load_file(str(Path(__file__).parent / 'cryptainer_store.kv'))


class PassphrasesDialogContent(BoxLayout):
    pass


class CryptainerStoreScreen(Screen):

    #: The container storage managed by this Screen, might be None if unset
    filesystem_cryptainer_storage = ObjectProperty(None, allownone=True)

    def _get_selected_cryptainer_names(self):
        cryptainer_names = []
        for cryptainer_entry in self.ids.cryptainer_table.children:
            if getattr(cryptainer_entry, "selected", None):  # Beware of WABigInformationBox
                assert cryptainer_entry.unique_identifier, cryptainer_entry.unique_identifier
                cryptainer_names.append(cryptainer_entry.unique_identifier)
        #print(">>>>> extract_selected_cryptainer_names", container_names)
        return cryptainer_names

    @safe_catch_unhandled_exception
    def get_detected_cryptainer(self):
        # Use this to profile slow list creation
        #import cProfile
        #cProfile.runctx("self._get_detected_cryptainer()", locals=locals(), globals=globals(), sort="cumulative")
        self._get_detected_cryptainer()

    def _get_detected_cryptainer(self):
        # FIXME use RecycleView instead for performance!!
        # https://stackoverflow.com/questions/70333878/kivymd-recycleview-has-low-fps-lags

        cryptainers_page_ids = self.ids

        #self.root.ids.screen_manager.get_screen(
        #    "Container_management"
        #).ids
        cryptainers_page_ids.cryptainer_table.clear_widgets()
        cryptainers_page_ids.cryptainer_table.do_layout()  # Prevents bug with "not found" message position

        #print(">>>>>>>>>>>>>self.filesystem_cryptainer_storage, ", self.filesystem_cryptainer_storage)
        if self.filesystem_cryptainer_storage is None:
            display_layout = Factory.WABigInformationBox()
            display_layout.ids.inner_label.text = tr._("Container storage is invalid")  # FIXME simplify this
            cryptainers_page_ids.cryptainer_table.add_widget(display_layout)
            return

        cryptainer_names = self.filesystem_cryptainer_storage.list_cryptainer_names(as_sorted=True)

        if not cryptainer_names:
            display_layout = Factory.WABigInformationBox()
            display_layout.ids.inner_label.text = tr._("No containers found")
            cryptainers_page_ids.cryptainer_table.add_widget(display_layout)
            return

        self.check_box_cryptainer_uuid_dict = {}
        self.btn_cryptainer_uuid_dict = {}

        self.cryptainer_checkboxes = []

        for index, cryptainer_name in enumerate(reversed(cryptainer_names), start=1):

            cryptainer_label = tr._("N° {index}: {container_name}").format(index=index, cryptainer_name=cryptainer_name)
            cryptainer_entry = Factory.WASelectableListItemEntry(
                    text=cryptainer_label)  # FIXME RENAME THIS
            cryptainer_entry.unique_identifier = cryptainer_name
            #selection_checkbox = container_entry.ids.selection_checkbox

            #def selection_callback(widget, value, container_name=container_name):  # Force container_name save here, else scope bug
            #    self.check_box_authentication_device_checked(device_uid=device_uid, is_selected=value)
            #selection_checkbox.bind(active=selection_callback)

            def information_callback(widget, cryptainer_name=cryptainer_name):  # Force device_uid save here, else scope bug
                self.show_cryptainer_details(cryptainer_name=cryptainer_name)
            information_icon = cryptainer_entry.ids.information_icon
            information_icon.bind(on_press=information_callback)

            cryptainers_page_ids.cryptainer_table.add_widget(cryptainer_entry)
            """
            my_check_box = CheckBox(active=False,
                                    size_hint=(0.1, None), height=40)
            my_check_box._cryptainer_name = container_name
            #my_check_box.bind(active=self.check_box_cryptainer_checked)
            self.container_checkboxes.append(my_check_box)

            my_check_btn = Button(
                text="N° %s:  %s"
                % (index, container_name),
                size_hint=(0.9, None),
                background_color=(1, 1, 1, 0.01),
                on_release=functools.partial(self.show_cryptainer_details, container_name=container_name),
                height=40,
            )"""
            '''
            self.check_box_cryptainer_uuid_dict[my_check_box] = [
                str(container[0]["container_uid"]),
                str(container[1]),
            ]
            self.btn_cryptainer_uuid_dict[my_check_btn] = [
                str(container[0]["container_uid"]),
                str(container[1]),
            ]
            '''
            """
            layout = BoxLayout(
                orientation="horizontal",
                pos_hint={"center": 1, "top": 1},
                padding=[20, 0],
            )
            layout.add_widget(my_check_box)
            layout.add_widget(my_check_btn)
            """
            #containers_page_ids.container_table.add_widget(my_check_box)
            #containers_page_ids.container_table.add_widget(my_check_btn)

        #print("self.container_checkboxes", self.container_checkboxes)

    def get_selected_cryptainer_names(self):

        cryptainers_page_ids = self.ids

        cryptainer_names = []

        checkboxes = list(reversed(cryptainers_page_ids.cryptainer_table.children))[::2]

        for checkbox in checkboxes:
            if checkbox.active:
                cryptainer_names.append(checkbox._cryptainer_name)

        #print("container_names", container_names)
        return cryptainer_names

    def show_cryptainer_details(self, cryptainer_name):
        """
        Display the contents of container
        """
        assert self.filesystem_cryptainer_storage, self.filesystem_cryptainer_storage  # By construction...
        try:
            cryptainer = self.filesystem_cryptainer_storage.load_cryptainer_from_storage(cryptainer_name)
            all_dependencies = gather_escrow_dependencies([cryptainer])
            interesting_dependencies = [d[0] for d in list(all_dependencies["encryption"].values())]
            cryptainer_repr = "\n".join(str(escrow) for escrow in interesting_dependencies)
            #container_repr = pprint.pformat(interesting_dependencies, indent=2)[:800]  # LIMIT else pygame.error: Width or height is too large
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


    def open_dialog_delete_cryptainer(self):

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
                    text="Confirm deletion", on_release=lambda *args: (close_current_dialog(), self.delete_cryptainers(cryptainer_names=cryptainer_names))
                ),]
        )

    def delete_cryptainers(self, cryptainer_names):
        assert self.filesystem_cryptainer_storage, self.filesystem_cryptainer_storage  # By construction...
        for cryptainer_name in cryptainer_names:
            try:
                self.filesystem_cryptainer_storage.delete_cryptainer(cryptainer_name)
            except FileNotFoundError:
                pass  # File has probably been puregd already

        self.get_detected_cryptainer()  # FIXME rename


    def open_dialog_decipher_cryptainer(self):

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
        filesystem_key_storage_pool = self.filesystem_cryptainer_storage._key_storage_pool  # FIXME add public getter
        key_storage_metadata = filesystem_key_storage_pool.list_imported_key_storage_metadata()

        cryptainers = [self.filesystem_cryptainer_storage.load_cryptainer_from_storage(x) for x in cryptainer_names]
        dependencies = gather_escrow_dependencies(cryptainers)

        # BEWARE this only works for "authentication device" escrows!
        # TODO make this more generic with support for remote escrow!
        relevant_authentication_device_uids = [escrow[0]["authentication_device_uid"] for escrow in dependencies["encryption"].values()]

        relevant_key_storage_metadata = sorted([y for (x,y) in key_storage_metadata.items()
                                                if x in relevant_authentication_device_uids], key = lambda d: d["user"])

        #print("--------------")
        #pprint.pprint(relevant_key_storage_metadata)


        content_cls = PassphrasesDialogContent()

        #print(">>>>>>relevant_key_storage_metadata", relevant_key_storage_metadata)
        for metadata in relevant_key_storage_metadata:
            hint_text="Passphrase for user %s (hint: %s)" % (metadata["user"], metadata["passphrase_hint"])
            _widget = TextInput(hint_text=hint_text)

            '''MDTextField(hint_text="S SSSSSSSS z z",
                              helper_text="Passphrase for user %s (hint: %s)" % (metadata["user"], metadata["passphrase_hint"]),
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
                    on_release=lambda *args: (close_current_dialog(), self.decipher_cryptainers(cryptainer_names=cryptainer_names, input_content_cls=content_cls)),
                ),]
        )

    def decipher_cryptainers(self, cryptainer_names, input_content_cls):
        assert self.filesystem_cryptainer_storage, self.filesystem_cryptainer_storage  # By construction...

        inputs = list(reversed(input_content_cls.children))
        passphrases = [i.text for i in inputs]
        passphrase_mapper = {None: passphrases}  # For now we regroup all passphrases together

        errors = []

        for cryptainer_name in cryptainer_names:
            try:
                EXTERNAL_DATA_EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
                # FIXME make this asynchronous, to avoid stalling the app!
                result = self.filesystem_cryptainer_storage.decrypt_cryptainer_from_storage(cryptainer_name, passphrase_mapper=passphrase_mapper)
                target_path = EXTERNAL_DATA_EXPORTS_DIR / (Path(cryptainer_name).with_suffix(""))
                target_path.write_bytes(result)
                #print(">> Successfully exported data file to %s" % target_path)
            except Exception as exc:
                #print(">>>>> close_dialog_decipher_cryptainer() exception thrown:", exc)  # TEMPORARY
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

    @safe_catch_unhandled_exception
    def __UNUSED_offloaded_attempt_cryptainer_decryption(self, cryptainer_filepath):  #FIXME move out of here
        logger.info("Decryption requested for container %s", cryptainer_filepath)
        target_directory = EXTERNAL_DATA_EXPORTS_DIR.joinpath(
            os.path.basename(cryptainer_filepath)
        )
        target_directory.mkdir(
            exist_ok=True
        )  # Double exports would replace colliding files
        cryptainer = load_cryptainer_from_filesystem(cryptainer_filepath, include_data_ciphertext=True)
        tarfile_bytes = decrypt_data_from_cryptainer(
            cryptainer, key_storage_pool=self._key_storage_pool
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
    def __UNUSED_attempt_cryptainer_decryption(self, cryptainer_filepath: str):  #FIXME move out of here
        cryptainer_filepath = Path(cryptainer_filepath)
        return self._offload_task(self._offloaded_attempt_cryptainer_decryption, cryptainer_filepath=cryptainer_filepath)

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
        escrow_dependencies = gather_escrow_dependencies(containers=containers)

        decryption_authorizations = request_decryption_authorizations(
            escrow_dependencies=escrow_dependencies,
            key_storage_pool=filesystem_key_storage_pool,
            request_message="Need decryptions"
        )
        for container in containers:
            decrypt_data_from_cryptainer(container=container)
            """