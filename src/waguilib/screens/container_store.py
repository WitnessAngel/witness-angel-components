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

from wacryptolib.container import gather_escrow_dependencies
from waguilib.widgets.popups import close_current_dialog, dialog_with_close_button

Builder.load_file(str(Path(__file__).parent / 'container_store.kv'))


class PassphrasesDialogContent(BoxLayout):
    pass


class ContainerStoreScreen(Screen):

    #: The container storage managed by this Screen, might be None if unset
    filesystem_container_storage = ObjectProperty(None, allownone=True)

    def _get_selected_container_names(self):
        container_names = []
        for container_entry in self.ids.container_table.children:
            if getattr(container_entry, "selected", None):  # Beware of WABigInformationBox
                assert container_entry.unique_identifier, container_entry.unique_identifier
                container_names.append(container_entry.unique_identifier)
        #print(">>>>> extract_selected_container_names", container_names)
        return container_names

    @safe_catch_unhandled_exception
    def get_detected_container(self):
        containers_page_ids = self.ids

        #self.root.ids.screen_manager.get_screen(
        #    "Container_management"
        #).ids
        containers_page_ids.container_table.clear_widgets()
        containers_page_ids.container_table.do_layout()  # Prevents bug with "not found" message position

        #print(">>>>>>>>>>>>>self.filesystem_container_storage, ", self.filesystem_container_storage)
        if self.filesystem_container_storage is None:
            display_layout = Factory.WABigInformationBox()
            display_layout.ids.inner_label.text = tr._("Container storage is invalid")  # FIXME simplify this
            containers_page_ids.container_table.add_widget(display_layout)
            return

        container_names = self.filesystem_container_storage.list_container_names(as_sorted=True)

        if not container_names:
            display_layout = Factory.WABigInformationBox()
            display_layout.ids.inner_label.text = tr._("No containers found")
            containers_page_ids.container_table.add_widget(display_layout)
            return

        self.check_box_container_uuid_dict = {}
        self.btn_container_uuid_dict = {}

        self.container_checkboxes = []

        for index, container_name in enumerate(container_names, start=1):

            container_label = tr._("N° %s:  %s") % (index, container_name)
            container_entry = Factory.WASelectableListItemEntry(
                    text=container_label)  # FIXME RENAME THIS
            container_entry.unique_identifier = container_name
            #selection_checkbox = container_entry.ids.selection_checkbox

            #def selection_callback(widget, value, container_name=container_name):  # Force container_name save here, else scope bug
            #    self.check_box_authentication_device_checked(device_uid=device_uid, is_selected=value)
            #selection_checkbox.bind(active=selection_callback)

            def information_callback(widget, container_name=container_name):  # Force device_uid save here, else scope bug
                self.show_container_details(container_name=container_name)
            information_icon = container_entry.ids.information_icon
            information_icon.bind(on_press=information_callback)

            containers_page_ids.container_table.add_widget(container_entry)
            """
            my_check_box = CheckBox(active=False,
                                    size_hint=(0.1, None), height=40)
            my_check_box._container_name = container_name
            #my_check_box.bind(active=self.check_box_container_checked)
            self.container_checkboxes.append(my_check_box)

            my_check_btn = Button(
                text="N° %s:  %s"
                % (index, container_name),
                size_hint=(0.9, None),
                background_color=(1, 1, 1, 0.01),
                on_release=functools.partial(self.show_container_details, container_name=container_name),
                height=40,
            )"""
            '''
            self.check_box_container_uuid_dict[my_check_box] = [
                str(container[0]["container_uid"]),
                str(container[1]),
            ]
            self.btn_container_uuid_dict[my_check_btn] = [
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

    def get_selected_container_names(self):

        containers_page_ids = self.ids

        container_names = []

        checkboxes = list(reversed(containers_page_ids.container_table.children))[::2]

        for checkbox in checkboxes:
            if checkbox.active:
                container_names.append(checkbox._container_name)

        #print("container_names", container_names)
        return container_names

    def show_container_details(self, container_name):
        """
        Display the contents of container
        """
        assert self.filesystem_container_storage, self.filesystem_container_storage  # By construction...
        try:
            container = self.filesystem_container_storage.load_container_from_storage(container_name)
            all_dependencies = gather_escrow_dependencies([container])
            interesting_dependencies = [d[0] for d in list(all_dependencies["encryption"].values())]
            container_repr = pprint.pformat(interesting_dependencies, indent=2)[:800]  # LIMIT else pygame.error: Width or height is too large
        except Exception as exc:
            container_repr = repr(exc)

        self.open_container_details_dialog(container_repr, info_container=container_name)

    def open_container_details_dialog(self, message, info_container):
        dialog_with_close_button(
            close_btn_label=tr._("Close"),
            title=str(info_container),
            text=message,
        )
        '''
        self.dialog = MDDialog(
            title=str(info_container),
            text=message,
            size_hint=(0.8, 1),
            buttons=[MDFlatButton(text=tr._("Close"), on_release=lambda *args: close_current_dialog())],
        )
        self.dialog.open()
        '''


    def open_dialog_delete_container(self):

        container_names = self._get_selected_container_names()
        if not container_names:
            return

        message = "Are you sure you want to delete %s container(s)?" % len(container_names)
        """
        self.list_chbx_active = []
        for chbx in self.check_box_container_uuid_dict:
            if chbx.active:
                self.list_chbx_active.append(chbx)

        count_container_checked =len(self.list_chbx_active)
        if count_container_checked == 1:
            messge = " do you want to delete these container?"
        elif count_container_checked > 1:
            messge = (
                " do you want to delete these %d containers"
                % count_container_checked
            )
        """
        dialog_with_close_button(
            close_btn_label=tr._("Cancel"),
            title=tr._("Container deletion confirmation"),
            text=message,
            buttons=[
                MDFlatButton(
                    text="Confirm deletion", on_release=lambda *args: (close_current_dialog(), self.delete_containers(container_names=container_names))
                ),]
        )

    def delete_containers(self, container_names):
        assert self.filesystem_container_storage, self.filesystem_container_storage  # By construction...
        for container_name in container_names:
            try:
                self.filesystem_container_storage.delete_container(container_name)
            except FileNotFoundError:
                pass  # File has probably been puregd already

        self.get_detected_container()  # FIXME rename


    def open_dialog_decipher_container(self):

        container_names = self._get_selected_container_names()
        if not container_names:
            return

        message = "Decrypt %s container(s)?" % len(container_names)

        """
        self.list_chbx_active = []
        for chbx in self.check_box_container_uuid_dict:
            if chbx.active:
                self.list_chbx_active.append(chbx)

        count_container_checked = len(self.list_chbx_active)

        if count_container_checked == 1:
            messge = " do you want to decipher these container?"
        elif count_container_checked > 1:
            messge = (
                    " Do you want to decipher these %d containers" % count_container_checked
            )
        """

        assert self.filesystem_container_storage, self.filesystem_container_storage  # By construction...
        filesystem_key_storage_pool = self.filesystem_container_storage._key_storage_pool  # FIXME add public getter
        key_storage_metadata = filesystem_key_storage_pool.list_imported_key_storage_metadata()

        containers = [self.filesystem_container_storage.load_container_from_storage(x) for x in container_names]
        dependencies = gather_escrow_dependencies(containers)

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
                    on_release=lambda *args: (close_current_dialog(), self.decipher_containers(container_names=container_names, input_content_cls=content_cls)),
                ),]
        )

    def decipher_containers(self, container_names, input_content_cls):
        assert self.filesystem_container_storage, self.filesystem_container_storage  # By construction...

        inputs = list(reversed(input_content_cls.children))
        passphrases = [i.text for i in inputs]
        passphrase_mapper = {None: passphrases}  # For now we regroup all passphrases together

        errors = []

        for container_name in container_names:
            try:
                EXTERNAL_DATA_EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
                # FIXME make this asynchronous, to avoid stalling the app!
                result = self.filesystem_container_storage.decrypt_container_from_storage(container_name, passphrase_mapper=passphrase_mapper)
                target_path = EXTERNAL_DATA_EXPORTS_DIR / (Path(container_name).with_suffix(""))
                target_path.write_bytes(result)
                #print(">> Successfully exported data file to %s" % target_path)
            except Exception as exc:
                #print(">>>>> close_dialog_decipher_container() exception thrown:", exc)  # TEMPORARY
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
    def __UNUSED_offloaded_attempt_container_decryption(self, container_filepath):  #FIXME move out of here
        logger.info("Decryption requested for container %s", container_filepath)
        target_directory = EXTERNAL_DATA_EXPORTS_DIR.joinpath(
            os.path.basename(container_filepath)
        )
        target_directory.mkdir(
            exist_ok=True
        )  # Double exports would replace colliding files
        container = load_container_from_filesystem(container_filepath, include_data_ciphertext=True)
        tarfile_bytes = decrypt_data_from_container(
            container, key_storage_pool=self._key_storage_pool
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

    ##@osc.address_method("/attempt_container_decryption")
    @safe_catch_unhandled_exception
    def __UNUSED_attempt_container_decryption(self, container_filepath: str):  #FIXME move out of here
        container_filepath = Path(container_filepath)
        return self._offload_task(self._offloaded_attempt_container_decryption, container_filepath=container_filepath)

        """
        print("The written sentence is passphrase : %s" % input)
        containers = []
        for chbx in self.check_box_container_uuid_dict:
            if chbx.active:
                print(
                    "Decipher container | with ID_container %s",
                    self.check_box_container_uuid_dict[chbx],
                )
                container = load_container_from_filesystem(
                    container_filepath=Path(
                        ".container_storage_ward".format(self.check_box_container_uuid_dict[chbx][1])
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
            decrypt_data_from_container(container=container)
            """
