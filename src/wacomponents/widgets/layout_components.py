import textwrap
from pathlib import Path

from kivy.factory import Factory
from kivy.lang import Builder
from kivy.properties import ObjectProperty, Clock
from kivy.uix.accordion import Accordion
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.settings import SettingItem, SettingString
from kivy.uix.textinput import TextInput
from kivymd.app import MDApp
from kivymd.uix.menu import MDDropdownMenu

from wacomponents.default_settings import IS_MOBILE
from wacomponents.i18n import tr


# FIXME RENAME THIS MODULE AS MISC_WIDGETS??


def activate_widget_debug_outline():
    """Create a dotted outline around widgets, to help layout setup."""
    widget_outline_hack = textwrap.dedent(
        """
    <Widget>:
        canvas.after:
            Line:
                rectangle: self.x+1,self.y+1,self.width-1,self.height-1
                dash_offset: 5
                dash_length: 3
    """
    )

    Builder.load_string(widget_outline_hack)


def load_layout_helper_widgets():
    Builder.load_file(str(Path(__file__).parent / "layout_components.kv"))  # TODO use "with_name"


# FIXME use or remove?
# <ConsoleOutput>:
#    readonly: True
#    padding: 6, 6
#    size_hint: (1, None)


def build_fallback_information_box(message):
    display_layout = Factory.WABigInformationBox()
    display_layout.message = message
    return display_layout


class SettingStringTruncated(SettingItem):

    # We recopy interesting bits from SettingString, we can't inherit it due to KV styles applied

    popup = ObjectProperty(None, allownone=True)
    textinput = ObjectProperty(None)

    on_panel = SettingString.on_panel
    _dismiss = SettingString._dismiss
    _validate = SettingString._validate
    _create_popup = SettingString._create_popup


class LanguageSwitcherScreenMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        language_menu_items = [
            {"text": lang, "viewclass": "OneLineListItem", "on_release": lambda x=lang_code: self.on_language_change(x)}
            for (lang, lang_code) in [("English", "en"), ("Français", "fr")]
        ]

        self._language_selector_menu = MDDropdownMenu(
            # header_cls=Factory.LanguageMenuHeader(),
            # caller=self.screen.ids.button,
            items=language_menu_items,
            width_mult=2,
            position="bottom",
            ver_growth="down",
            max_height="110dp",
        )

    def language_menu_open(self, button):
        self._language_selector_menu.caller = button
        self._language_selector_menu.open()

    def on_language_change(self, lang_code):
        self._language_selector_menu.dismiss()
        tr.switch_lang(lang_code)
        MDApp.get_running_app().on_language_change(lang_code)  # Propagate to App


class WASelectableLabel(TextInput):

    _tokenize_delimiters = TextInput._tokenize_delimiters + "/\\"  # Help properly cut FILEPATHS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if IS_MOBILE:
            self.keyboard_mode = "managed"  # Do not auto-show the keyboard on mobile devices
            # Else let it be, so that copy/paste shortcuts work

        # EVEN IF READONLY, we need this to prevent selection bugs on mobile platform
        def fix_focusability(x):
            self.is_focusable = True

        Clock.schedule_once(fix_focusability)

    def _on_textinput_focused(self, instance, value, *largs):
        res = super()._on_textinput_focused(instance, value, *largs)

        if value:
            # HORRIBLE hack so that FocusBehaviour._handle_post_on_touch_up() unfocuses
            # this widget when user touches outside it
            FocusBehavior._keyboards[None] = self

        return res


class GrowingAccordion(Accordion):
    def _do_layout(self, dt):
        children = self.children
        if children:
            all_collapsed = all(x.collapse for x in children)
        else:
            all_collapsed = False

        if all_collapsed:
            children[0].collapse = False

        orientation = self.orientation
        min_space = self.min_space
        min_space_total = len(children) * self.min_space
        w, h = self.size
        x, y = self.pos

        if orientation == "horizontal":
            children = reversed(children)

        display_space_total = 0
        for child in children:
            if orientation == "horizontal":
                child_display_space = child.container.children[0].minimum_width
            else:
                child_display_space = child.container.children[0].minimum_height

            child_space = min_space
            child_space += child_display_space * (1 - child.collapse_alpha)

            display_space_total += child_space

            child._min_space = min_space
            child.x = x
            child.y = y
            child.orientation = self.orientation
            if orientation == "horizontal":
                child.content_size = child_display_space, h
                child.width = child_space
                child.height = h
                x += child_space
            else:
                child.content_size = w, child_display_space
                child.width = w
                child.height = child_space
                y += child_space

        if orientation == "horizontal":
            self.width = display_space_total
        else:
            self.height = display_space_total
