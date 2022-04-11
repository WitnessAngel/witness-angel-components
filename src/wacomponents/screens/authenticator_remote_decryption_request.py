from pathlib import Path

from kivy.lang import Builder
from kivy.logger import Logger as logger
from kivy.properties import ObjectProperty, BooleanProperty, StringProperty
from kivy.uix.accordion import AccordionItem
from kivy.uix.boxlayout import BoxLayout

from kivymd.app import MDApp
from kivy.factory import Factory
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.screen import Screen
from kivymd.uix.tab import MDTabsBase
from kivymd.uix.list import MDList

from wacomponents.i18n import tr
from wacomponents.widgets.popups import help_text_popup, display_info_toast, dialog_with_close_button


Builder.load_file(str(Path(__file__).parent / 'authenticator_remote_decryption_request.kv'))


class Tab(MDFloatLayout, MDTabsBase):
    """Class implementing content for a tab."""


class RemoteDecryptionRequestScreen(Screen):
    index = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._app = MDApp.get_running_app()

    def go_to_home_screen(self):  # Fixme deduplicate and push to App!
        self.manager.current = "authenticator_selector_screen"

    def add_remote_decryption_request(self, decryption_request_uid):

        decryption_request_item = AccordionItem(title='Title %s' % decryption_request_uid)

        layout = BoxLayout(orientation='vertical')

        buttongrid = Factory.WAButtonsGridLayout()

        acceptedbutton = Factory.WAGreenButton(text="Accepted")
        rejectedbutton = Factory.WARedButton(text="Rejected")

        buttongrid.add_widget(acceptedbutton)
        buttongrid.add_widget(rejectedbutton)

        scrollview = Factory.WAVerticalScrollView()
        symkey_decryption_list = MDList()

        for key_index in range(1, 4):
            symkey_decryption_label = tr._("N° {key_index}: {symkey_decryption}").format(key_index=key_index, symkey_decryption="Symkey_decryption_uid "+str(key_index))
            symkey_decryption_entry = Factory.WAIconListItemEntry(text=symkey_decryption_label)  # FIXME RENAME THIS

            def information_callback(widget):  # Force keystore_uid save here, else scope bug
                self.show_symkey_decryption_details(keychain_uid="rrrrrrrrrr")

            information_icon = symkey_decryption_entry.ids.information_icon
            information_icon.bind(on_press=information_callback)

            symkey_decryption_list.add_widget(symkey_decryption_entry)

        scrollview.add_widget(symkey_decryption_list)

        layout.add_widget(buttongrid)

        layout.add_widget(scrollview)

        decryption_request_item.add_widget(layout)

        self.ids.pending_decryption_request.add_widget(decryption_request_item)

    def show_symkey_decryption_details(self, keychain_uid):
        dialog_with_close_button(
            close_btn_label=tr._("Close"),
            title=tr._("Symkeys Decryption Details {keychain_uid} ").format(keychain_uid=keychain_uid),
            text="Details",
        )

    def add_many_accordion_test(self):
        # TODO add list_decryption_request to parameter of this function

       # if self.list_decryption_request is None:
           # display_layout = Factory.WABigInformationBox()
            #display_layout.ids.inner_label.text = tr._("Aucune demande de déchiffrement")  # FIXME simplify this
            #self.ids.pending_decryption_request.add_widget(display_layout)
            #return

        for i in range(1, 6):
            self.add_remote_decryption_request(decryption_request_uid="decryption_request_uid " + str(i))
