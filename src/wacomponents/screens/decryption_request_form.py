from pathlib import Path
from textwrap import dedent

from kivy.factory import Factory
from kivy.lang import Builder
from kivy.properties import ObjectProperty, BooleanProperty
from kivymd.app import MDApp
from kivymd.uix.screen import Screen

from wacomponents.i18n import tr

Builder.load_file(str(Path(__file__).parent / 'decryption_request_form.kv'))


class DecryptionRequestFormScreen(Screen):
    selected_cryptainer_names = ObjectProperty(None, allownone=True)
    trustee_data = ObjectProperty(None, allownone=True)

    def __init__(self, *args, **kwargs):
        self._app = MDApp.get_running_app()
        super().__init__(*args, **kwargs)

    def go_to_previous_screen(self):
        self.manager.current = "CryptainerDecryption"

    def display_decryption_request_form(self):
        self.ids.authenticator_checklist.clear_widgets()

        # Display summary
        cryptainers_name = ""

        for cryptainer_name in self.selected_cryptainer_names:
            cryptainers_name = cryptainers_name + "\n\t" + str(cryptainer_name)

        _displayed_values = dict(
            containers_selected= cryptainers_name,
            gateway_url=self._app.get_wagateway_url()
        )

        decryption_request_summary_text = dedent(tr._("""\
                                            Container(s) selected: {containers_selected}
                                            Gateway url: {gateway_url}                                           
                                        """)).format(**_displayed_values)

        self.ids.decryption_request_summary.text = decryption_request_summary_text

        # Display the list of required authenticators
        for trustee_info, trustee_keypair_identifiers in self.trustee_data:
            keystore_uid = trustee_info["keystore_uid"]

            self.ids.authenticator_checklist.add_widget(
                Factory.ListItemWithCheckbox(
                    text=tr._("Authenticator: {keystore_uid}").format(keystore_uid=keystore_uid))
            )
