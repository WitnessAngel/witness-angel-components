from pathlib import Path

from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.screen import Screen

from wacomponents.widgets.layout_components import LanguageSwitcherScreenMixin

Builder.load_file(str(Path(__file__).parent / 'recorder_homepage.kv'))



class RecorderHomepageScreen(LanguageSwitcherScreenMixin, Screen):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._app = MDApp.get_running_app()

    def language_menu_select(self, lang_code):
        super().language_menu_select(lang_code)
        self._app.refresh_checkup_status()  # Refresh translation of Drive etc.
