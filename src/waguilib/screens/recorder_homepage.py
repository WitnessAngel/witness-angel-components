import functools
import pprint
from pathlib import Path

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

from waguilib.importable_settings import EXTERNAL_EXPORTS_DIR
from waguilib.logging.handlers import safe_catch_unhandled_exception

from wacryptolib.cryptainer import gather_trustee_dependencies
from waguilib.widgets.layout_components import LanguageSwitcherScreenMixin

Builder.load_file(str(Path(__file__).parent / 'recorder_homepage.kv'))



class LauncherWithImagePreviewScreen(LanguageSwitcherScreenMixin, Screen):
    pass
    """
    def __init__(self, **kwargs):
        self.title = "Witness Angel - WardProject"

        super(MainWindow, self).__init__(**kwargs)
    """
