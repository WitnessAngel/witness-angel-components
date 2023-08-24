from pathlib import Path

from kivy.lang import Builder
from kivy.properties import StringProperty, ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivymd.theming import ThemableBehavior
from kivymd.uix.list import OneLineIconListItem, MDList
from kivymd.uix.navigationdrawer import MDNavigationDrawer

Builder.load_file(str(Path(__file__).parent / "navigation_drawer.kv"))


class WaNavigationDrawer(MDNavigationDrawer):
    pass


class NavigationDrawerContent(BoxLayout):  # FIXME useless intermediate class?
    pass


class DrawerList(MDList, ThemableBehavior):
    def __obsolete_set_color_item(self, instance_item):
        """
        Called when tap on a menu item - UNSAFE SINCE WE CAN NAVIGATE ALSO DIFFERENTLY
        """
        for item in self.children:
            if instance_item.text == item.text:
                item.text_color = (0.1372, 0.2862, 0.5294, 1)
            else:
                item.text_color = (0, 0, 0, 1)


class NavigationDrawerItem(OneLineIconListItem):  # FIXME rename
    icon = StringProperty()
    text_color = ListProperty((0, 0, 0, 1))
