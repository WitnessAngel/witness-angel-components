from pathlib import Path

from kivy.clock import Clock
from kivy.config import Config
from kivy.lang import Builder
from kivy.properties import StringProperty, ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.screenmanager import ScreenManager
from kivy.uix.textinput import TextInput
from kivymd.uix.navigationdrawer import MDNavigationDrawer
from kivymd.uix.textfield import MDTextField
from kivymd.app import MDApp
from kivymd.theming import ThemableBehavior
from kivymd.uix.button import MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import OneLineIconListItem, MDList
from kivymd.uix.screen import Screen
from kivymd.uix.snackbar import Snackbar


Builder.load_file(str(Path(__file__).parent / 'navigation_drawer.kv'))


class WaNavigationDrawer(MDNavigationDrawer):
    pass


class ContentNavigationDrawer(BoxLayout):  # FIXME useless intermediate class?
    pass


class DrawerList(ThemableBehavior, MDList):
    def set_color_item(self, instance_item):
        """
        Called when tap on a menu item.
        """
        for item in self.children:
            if instance_item.text == item.text:
                item.text_color = (0.1372, 0.2862, 0.5294, 1)
            else:
                item.text_color = (0, 0, 0, 1)


class ItemDrawer(OneLineIconListItem):  # FIXME rename
    icon = StringProperty()
    text_color = ListProperty((0, 0, 0, 1))
