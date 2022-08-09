from pathlib import Path

from kivy.lang import Builder
from kivy.properties import ObjectProperty, BooleanProperty
from kivymd.uix.screen import Screen

from wacomponents.i18n import tr


Builder.load_file(str(Path(__file__).parent / 'revelation_request_error_report.kv'))


class RevelationRequestErrorReportScreen(Screen):
    error_report = ObjectProperty(None, allownone=True)

    def go_to_previous_screen(self):
        self.manager.current = "CryptainerDecryption"

    def display_revelation_request_error(self):
        self.ids.error_report.text = self.error_report
