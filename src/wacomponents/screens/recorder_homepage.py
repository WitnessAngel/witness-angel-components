from pathlib import Path

from kivy.lang import Builder
from kivymd.uix.screen import Screen

from wacomponents.widgets.layout_components import LanguageSwitcherScreenMixin

Builder.load_file(str(Path(__file__).parent / 'recorder_homepage.kv'))



class LauncherWithImagePreviewScreen(LanguageSwitcherScreenMixin, Screen):
    pass
    """
    def __init__(self, **kwargs):
        self.title = "Witness Angel - WardProject"

        super(MainWindow, self).__init__(**kwargs)
    """
