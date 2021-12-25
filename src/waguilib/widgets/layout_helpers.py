import textwrap
from pathlib import Path

from kivy.lang import Builder
from kivymd.uix.menu import MDDropdownMenu
from waguilib.i18n import tr

def activate_widget_debug_outline():
    """Create a dotted outline around widgets, to help layout setup."""
    widget_outline_hack = textwrap.dedent("""
    <Widget>:
        canvas.after:
            Line:
                rectangle: self.x+1,self.y+1,self.width-1,self.height-1
                dash_offset: 5
                dash_length: 3
    """)

    Builder.load_string(widget_outline_hack)


def load_layout_helper_widgets():
    Builder.load_file(str(Path(__file__).parent / 'layout_helpers.kv'))  # TODO use "with_name"

# FIXME use or remove?
#<ConsoleOutput>:
#    readonly: True
#    padding: 6, 6
#    size_hint: (1, None)


class LanguageSwitcherScreenMixin:
    def __init__(self, *args, **kwargs):
        super().__init__( *args, **kwargs)

        language_menu_items = [
            {
                "text": lang,
                "viewclass": "OneLineListItem",
                "on_release": lambda x=lang_code: self.language_menu_select(x),
            } for (lang, lang_code) in [("English", "en"), ("French", "fr")]
        ]

        self._language_selector_menu = MDDropdownMenu(
            #header_cls=Factory.LanguageMenuHeader(),
            #caller=self.screen.ids.button,
            items=language_menu_items,
            width_mult=2,
            position="bottom",
            ver_growth="down",
            max_height="110dp",
        )

    def language_menu_open(self, button):
        self._language_selector_menu.caller = button
        self._language_selector_menu.open()

    def language_menu_select(self, lang_code):
        self._language_selector_menu.dismiss()
        tr.switch_lang(lang_code)
