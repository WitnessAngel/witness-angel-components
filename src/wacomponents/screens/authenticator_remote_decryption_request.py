from collections import OrderedDict
from pathlib import Path
from textwrap import dedent
from uuid import UUID

from kivy.lang import Builder
from kivy.logger import Logger as logger
from kivy.properties import ObjectProperty, BooleanProperty, StringProperty
from kivy.uix.accordion import AccordionItem, Accordion
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput

from kivymd.app import MDApp
from kivy.factory import Factory
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.screen import Screen
from kivymd.uix.tab import MDTabsBase
from kivymd.uix.list import MDList

from wacomponents.i18n import tr
from wacomponents.utilities import shorten_uid
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

    @staticmethod
    def list_authenticator_decryption_requests():

        list_authenticator_decryption_requests = \
            [OrderedDict([('public_authenticator', OrderedDict([('keystore_owner', 'keystore_owner'),
                                                                ('keystore_uid',
                                                                 UUID('0f01264a-87b2-3651-65b8-7735576ec680')),
                                                                ('public_keys', [OrderedDict([('keychain_uid', UUID(
                                                                    '0f01264a-87b2-9630-5ce2-5c006421bb85')),
                                                                                              ('key_algo', 'RSA_OAEP'),
                                                                                              ('key_value',
                                                                                               b'\xb1{\x1dr\x14\r!\xc1:\xd8\x1e\x95z\xa2\xea\x08\xf4g\xd8\xd0')]),
                                                                                 OrderedDict([('keychain_uid', UUID(
                                                                                     '0f01264a-87b2-05d9-fce4-e3566f06db24')),
                                                                                              ('key_algo', 'RSA_OAEP'),
                                                                                              ('key_value',
                                                                                               b'\xf0\xab \x92#R\x12\xdb\xcc\xd6\xfbag\x0e-\xb23\xff%\xba')])])])),
                          ('decryption_request_uid', '0f01264a-dd8d-4ee0-e7cf-41712f6c8acb'),
                          ('requester_uid', UUID('0f01264a-dd8d-5302-fa31-d0dd2f290bfd')),
                          ('description', 'Bien vouloir nous aider pour le dechiffrement de cette clé.'),
                          ('response_public_key', b'-\x07\x7f3]#\xa1\x82\xb1\xea\xd7\xec\x04\x0c\xbb\x97\xcfR\xa2,'),
                          ('request_status', 'PENDING'),
                          ('symkeys_decryption', [OrderedDict([('authenticator_public_key', OrderedDict(
                              [('keychain_uid', UUID('0f01264a-87b2-9630-5ce2-5c006421bb85')),
                               ('key_algo', 'RSA_OAEP'),
                               ('key_value', b'\xb1{\x1dr\x14\r!\xc1:\xd8\x1e\x95z\xa2\xea\x08\xf4g\xd8\xd0')])),
                                                               ('cryptainer_uid',
                                                                UUID('0f01264a-dd8d-482a-c54b-167e5d4363f7')),
                                                               ('cryptainer_metadata', {}),
                                                               ('request_data',
                                                                b'\xb1{\x1dr\x14\r!\xc1:\xd8\x1e\x95z\xa2\xea\x08\xf4g\xd8\xd0'),
                                                               ('response_data', b''),
                                                               ('decryption_status', 'PENDING')]),
                                                  OrderedDict([('authenticator_public_key', OrderedDict(
                                                      [('keychain_uid', UUID('0f01264a-87b2-05d9-fce4-e3566f06db24')),
                                                       ('key_algo', 'RSA_OAEP'),
                                                       ('key_value',
                                                        b'\xf0\xab \x92#R\x12\xdb\xcc\xd6\xfbag\x0e-\xb23\xff%\xba')])),
                                                               ('cryptainer_uid',
                                                                UUID('0f01264a-dd8d-8691-cf2d-613d29df23ad')),
                                                               ('cryptainer_metadata', {}),
                                                               ('request_data',
                                                                b'\xf0\xab \x92#R\x12\xdb\xcc\xd6\xfbag\x0e-\xb23\xff%\xba'),
                                                               ('response_data', b''),
                                                               ('decryption_status', 'PENDING')])])]),
             OrderedDict([('public_authenticator', OrderedDict([('keystore_owner', 'keystore_owner'),
                                                                ('keystore_uid',
                                                                 UUID('0f01264a-87b2-3651-65b8-7735576ec680')),
                                                                ('public_keys', [OrderedDict([('keychain_uid', UUID(
                                                                    '0f01264a-87b2-9630-5ce2-5c006421bb85')),
                                                                                              ('key_algo', 'RSA_OAEP'),
                                                                                              ('key_value',
                                                                                               b'\xb1{\x1dr\x14\r!\xc1:\xd8\x1e\x95z\xa2\xea\x08\xf4g\xd8\xd0')]),
                                                                                 OrderedDict([('keychain_uid', UUID(
                                                                                     '0f01264a-87b2-05d9-fce4-e3566f06db24')),
                                                                                              ('key_algo', 'RSA_OAEP'),
                                                                                              ('key_value',
                                                                                               b'\xf0\xab \x92#R\x12\xdb\xcc\xd6\xfbag\x0e-\xb23\xff%\xba')])])])),
                          ('decryption_request_uid', '0f01264a-dd8d-4ee0-e7cf-41712f6c8acb'),
                          ('requester_uid', UUID('0f01264a-dd8d-5302-fa31-d0dd2f290bfd')),
                          ('description', 'Bien vouloir nous aider pour le dechiffrement de cette clé.'),
                          ('response_public_key', b'-\x07\x7f3]#\xa1\x82\xb1\xea\xd7\xec\x04\x0c\xbb\x97\xcfR\xa2,'),
                          ('request_status', 'PENDING'),
                          ('symkeys_decryption', [OrderedDict([('authenticator_public_key', OrderedDict(
                              [('keychain_uid', UUID('0f01264a-87b2-9630-5ce2-5c006421bb85')),
                               ('key_algo', 'RSA_OAEP'),
                               ('key_value', b'\xb1{\x1dr\x14\r!\xc1:\xd8\x1e\x95z\xa2\xea\x08\xf4g\xd8\xd0')])),
                                                               ('cryptainer_uid',
                                                                UUID('0f01264a-dd8d-482a-c54b-167e5d4363f7')),
                                                               ('cryptainer_metadata', {}),
                                                               ('request_data',
                                                                b'\xb1{\x1dr\x14\r!\xc1:\xd8\x1e\x95z\xa2\xea\x08\xf4g\xd8\xd0'),
                                                               ('response_data', b''),
                                                               ('decryption_status', 'PENDING')]),
                                                  OrderedDict([('authenticator_public_key', OrderedDict(
                                                      [('keychain_uid', UUID('0f01264a-87b2-05d9-fce4-e3566f06db24')),
                                                       ('key_algo', 'RSA_OAEP'),
                                                       ('key_value',
                                                        b'\xf0\xab \x92#R\x12\xdb\xcc\xd6\xfbag\x0e-\xb23\xff%\xba')])),
                                                               ('cryptainer_uid',
                                                                UUID('0f01264a-dd8d-8691-cf2d-613d29df23ad')),
                                                               ('cryptainer_metadata', {}),
                                                               ('request_data',
                                                                b'\xf0\xab \x92#R\x12\xdb\xcc\xd6\xfbag\x0e-\xb23\xff%\xba'),
                                                               ('response_data', b''),
                                                               ('decryption_status', 'PENDING')])])]),
            OrderedDict([('public_authenticator', OrderedDict([('keystore_owner', 'keystore_owner'),
                                                                ('keystore_uid',
                                                                 UUID('0f01264a-87b2-3651-65b8-7735576ec680')),
                                                                ('public_keys', [OrderedDict([('keychain_uid', UUID(
                                                                    '0f01264a-87b2-9630-5ce2-5c006421bb85')),
                                                                                              ('key_algo', 'RSA_OAEP'),
                                                                                              ('key_value',
                                                                                               b'\xb1{\x1dr\x14\r!\xc1:\xd8\x1e\x95z\xa2\xea\x08\xf4g\xd8\xd0')]),
                                                                                 OrderedDict([('keychain_uid', UUID(
                                                                                     '0f01264a-87b2-05d9-fce4-e3566f06db24')),
                                                                                              ('key_algo', 'RSA_OAEP'),
                                                                                              ('key_value',
                                                                                               b'\xf0\xab \x92#R\x12\xdb\xcc\xd6\xfbag\x0e-\xb23\xff%\xba')])])])),
                          ('decryption_request_uid', '0f01264a-dd8d-4ee0-e7cf-41712f6c8acb'),
                          ('requester_uid', UUID('0f01264a-dd8d-5302-fa31-d0dd2f290bfd')),
                          ('description', 'Bien vouloir nous aider pour le dechiffrement de cette clé.'),
                          ('response_public_key', b'-\x07\x7f3]#\xa1\x82\xb1\xea\xd7\xec\x04\x0c\xbb\x97\xcfR\xa2,'),
                          ('request_status', 'PENDING'),
                          ('symkeys_decryption', [OrderedDict([('authenticator_public_key', OrderedDict(
                              [('keychain_uid', UUID('0f01264a-87b2-9630-5ce2-5c006421bb85')),
                               ('key_algo', 'RSA_OAEP'),
                               ('key_value', b'\xb1{\x1dr\x14\r!\xc1:\xd8\x1e\x95z\xa2\xea\x08\xf4g\xd8\xd0')])),
                                                               ('cryptainer_uid',
                                                                UUID('0f01264a-dd8d-482a-c54b-167e5d4363f7')),
                                                               ('cryptainer_metadata', {}),
                                                               ('request_data',
                                                                b'\xb1{\x1dr\x14\r!\xc1:\xd8\x1e\x95z\xa2\xea\x08\xf4g\xd8\xd0'),
                                                               ('response_data', b''),
                                                               ('decryption_status', 'PENDING')]),
                                                  OrderedDict([('authenticator_public_key', OrderedDict(
                                                      [('keychain_uid', UUID('0f01264a-87b2-05d9-fce4-e3566f06db24')),
                                                       ('key_algo', 'RSA_OAEP'),
                                                       ('key_value',
                                                        b'\xf0\xab \x92#R\x12\xdb\xcc\xd6\xfbag\x0e-\xb23\xff%\xba')])),
                                                               ('cryptainer_uid',
                                                                UUID('0f01264a-dd8d-8691-cf2d-613d29df23ad')),
                                                               ('cryptainer_metadata', {}),
                                                               ('request_data',
                                                                b'\xf0\xab \x92#R\x12\xdb\xcc\xd6\xfbag\x0e-\xb23\xff%\xba'),
                                                               ('response_data', b''),
                                                               ('decryption_status', 'PENDING')])])]),

            OrderedDict([('public_authenticator', OrderedDict([('keystore_owner', 'keystore_owner'),
                                                                ('keystore_uid',
                                                                 UUID('0f01264a-87b2-3651-65b8-7735576ec680')),
                                                                ('public_keys', [OrderedDict([('keychain_uid', UUID(
                                                                    '0f01264a-87b2-9630-5ce2-5c006421bb85')),
                                                                                              ('key_algo', 'RSA_OAEP'),
                                                                                              ('key_value',
                                                                                               b'\xb1{\x1dr\x14\r!\xc1:\xd8\x1e\x95z\xa2\xea\x08\xf4g\xd8\xd0')]),
                                                                                 OrderedDict([('keychain_uid', UUID(
                                                                                     '0f01264a-87b2-05d9-fce4-e3566f06db24')),
                                                                                              ('key_algo', 'RSA_OAEP'),
                                                                                              ('key_value',
                                                                                               b'\xf0\xab \x92#R\x12\xdb\xcc\xd6\xfbag\x0e-\xb23\xff%\xba')])])])),
                          ('decryption_request_uid', '0f01264a-de2a-12c1-b508- '),
                          ('requester_uid', UUID('0f01264a-dd8d-5302-fa31-d0dd2f290bfd')),
                          ('description', 'Bien vouloir nous aider pour le dechiffrement de cette clé.'),
                          ('response_public_key', b'-\x07\x7f3]#\xa1\x82\xb1\xea\xd7\xec\x04\x0c\xbb\x97\xcfR\xa2,'),
                          ('request_status', 'ACCEPTED'),
                          ('symkeys_decryption', [OrderedDict([('authenticator_public_key', OrderedDict(
                              [('keychain_uid', UUID('0f01264a-87b2-9630-5ce2-5c006421bb85')),
                               ('key_algo', 'RSA_OAEP'),
                               ('key_value', b'\xb1{\x1dr\x14\r!\xc1:\xd8\x1e\x95z\xa2\xea\x08\xf4g\xd8\xd0')])),
                                                               ('cryptainer_uid',
                                                                UUID('0f01264a-dd8d-482a-c54b-167e5d4363f7')),
                                                               ('cryptainer_metadata', {}), ('request_data',
                                                                                             b'\xb1{\x1dr\x14\r!\xc1:\xd8\x1e\x95z\xa2\xea\x08\xf4g\xd8\xd0'),
                                                               ('response_data', b''),
                                                               ('decryption_status', 'PENDING')]),
                                                  OrderedDict([('authenticator_public_key', OrderedDict(
                                                      [('keychain_uid', UUID('0f01264a-87b2-05d9-fce4-e3566f06db24')),
                                                       ('key_algo', 'RSA_OAEP'),
                                                       ('key_value',
                                                        b'\xf0\xab \x92#R\x12\xdb\xcc\xd6\xfbag\x0e-\xb23\xff%\xba')])),
                                                               ('cryptainer_uid',
                                                                UUID('0f01264a-dd8d-8691-cf2d-613d29df23ad')),
                                                               ('cryptainer_metadata', {}),
                                                               ('request_data',
                                                                b'\xf0\xab \x92#R\x12\xdb\xcc\xd6\xfbag\x0e-\xb23\xff%\xba'),
                                                               ('response_data', b''),
                                                               ('decryption_status', 'PENDING')])])])]

        return list_authenticator_decryption_requests

    def _add_to_display_single_remote_decryption_request(self, decryption_request):

        decryptionRequestEntry = Factory.DecryptionRequestEntry()

        decryptionRequestEntry.title = tr._("Request : {decryption_request_uid}").format(
            decryption_request_uid=decryption_request["decryption_request_uid"])

        _displayed_values = dict(
            public_authenticator=decryption_request["public_authenticator"]["keystore_owner"],
            requester_uid=decryption_request["requester_uid"],
            description=decryption_request["description"],
            response_public_key=decryption_request["response_public_key"]
        )

        decryption_request_summary_text = dedent(tr._("""\
                                    Authenticator: {public_authenticator}
                                    Requester ID: {requester_uid}
                                    Description: {description}
                                    Response public key: {response_public_key}
                                """)).format(**_displayed_values)

        decryptionRequestEntry.decryption_request_summary.text = decryption_request_summary_text


        for index, symkey_decryption in enumerate(decryption_request['symkeys_decryption'], start=1):
            symkey_decryption_label = tr._("N° {key_index}: {symkey_decryption} ({key_algo})"). \
                format(key_index=index, symkey_decryption=symkey_decryption["authenticator_public_key"]["keychain_uid"],
                       key_algo=symkey_decryption["authenticator_public_key"]["key_algo"])

            symkey_decryption_entry = Factory.WAIconListItemEntry(text=symkey_decryption_label)  # FIXME RENAME THIS

            def information_callback(widget,
                                     symkey_decryption=symkey_decryption):  # Force keystore_uid save here, else scope bug
                self.show_symkey_decryption_details(symkey_decryption=symkey_decryption)

            information_icon = symkey_decryption_entry.ids.information_icon
            information_icon.bind(on_press=information_callback)

            decryptionRequestEntry.symkeys_decryption.add_widget(symkey_decryption_entry)

        return decryptionRequestEntry

    def show_symkey_decryption_details(self, symkey_decryption):

        _displayed_values = dict(
            cryptainer_uid=symkey_decryption["cryptainer_uid"],
            cryptainer_metadata=symkey_decryption["cryptainer_metadata"],
            request_data=symkey_decryption["request_data"],
            decryption_status=symkey_decryption["decryption_status"]
        )

        symkey_decryption_info_text = dedent(tr._("""\
                                   Cryptainer uid: {cryptainer_uid}
                                   Cryptainer metadata: {cryptainer_metadata}
                                   Request data: {request_data}
                                   Decryption status: {decryption_status}
                               """)).format(**_displayed_values)
        dialog_with_close_button(
            close_btn_label=tr._("Close"),
            title=tr._("Symkey decryption {keychain_uid} ").format(keychain_uid=shorten_uid(symkey_decryption["authenticator_public_key"]["keychain_uid"])),
            text= symkey_decryption_info_text,
        )

    def add_remote_decryption_request(self, decryption_requests_per_status):  # TODO change name function
        # TODO add list_decryption_request to parameter of this function

        tab_per_status = dict(PENDING=self.ids.pending_decryption_request,
                              REJECTED=self.ids.rejected_decryption_request,
                              ACCEPTED=self.ids.accepted_decryption_request)

        for status, decryption_requests in decryption_requests_per_status.items():

            if not decryption_requests:
                display_layout = Factory.WABigInformationBox()
                display_layout.ids.inner_label.text = tr._("Aucune demande de déchiffrement")  # FIXME simplify this
                tab_per_status[status].add_widget(display_layout)
                return

            root = Accordion(orientation='vertical')
            for decryption_request in decryption_requests:
                decryption_request_item = self._add_to_display_single_remote_decryption_request(decryption_request=decryption_request)
                root.add_widget(decryption_request_item)
            tab_per_status[status].add_widget(root)

    def sort_list_decryption_request_per_status(self, list_authenticator_decryption_requests):
        DECRYPTION_REQUEST_STATUSES = ["PENDING", "ACCEPTED", "REJECTED"]  # KEEP IN SYNC with WASERVER
        decryption_requests_per_status = {
            DECRYPTION_REQUEST_STATUSES[0]: [],
            DECRYPTION_REQUEST_STATUSES[1]: [],
            DECRYPTION_REQUEST_STATUSES[2]: []
        }
        for decryption_request in list_authenticator_decryption_requests:
            decryption_requests_per_status[decryption_request["request_status"]].append(decryption_request)
        return decryption_requests_per_status

    def fetch_and_display_decryption_requests(self):
        list_authenticator_decryption_requests = self.list_authenticator_decryption_requests()

        decryption_requests_per_status = self.sort_list_decryption_request_per_status(
            list_authenticator_decryption_requests)
        self.add_remote_decryption_request(decryption_requests_per_status)
