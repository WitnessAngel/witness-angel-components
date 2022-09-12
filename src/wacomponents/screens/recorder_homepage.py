from pathlib import Path

from kivy.lang import Builder

from wacomponents.screens.base import WAScreenBase
from wacomponents.widgets.layout_components import LanguageSwitcherScreenMixin

Builder.load_file(str(Path(__file__).parent / 'recorder_homepage.kv'))


class RecorderHomepageScreen(LanguageSwitcherScreenMixin, WAScreenBase):

    def on_language_change(self, lang_code):
        super().on_language_change(lang_code)
        self._app.refresh_checkup_status()  # Refresh translation of Drive etc.
