# -*- coding: utf-8 -*-
from pathlib import Path

from kivy.app import App
from kivy.base import runTouchApp
from kivy.lang import Builder
from kivy.properties import (
    ObjectProperty,
    ListProperty,
    StringProperty,
    NumericProperty,
)
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput

Builder.load_file(str(Path(__file__).parent / 'logging_console.kv'))


class ConsoleOutput(TextInput):

    max_text_size = 10000

    _add_text_is_in_progress = False

    def __init__(self, **kwargs):
        super(ConsoleOutput, self).__init__(**kwargs)
        app = App.get_running_app()

    def is_locked(self):
        return ((self.parent.height >= self.height) or
                (self.parent.scroll_y <= 0.05))

    def scroll_to_bottom(self):
        self.parent.scroll_y = 0

    def add_text(self, text):

        if self._add_text_is_in_progress:
            return  # Logging recursion cna happen, due to Kivy GL events

        self._add_text_is_in_progress = True
        try:
            is_locked = self.is_locked()

            text += "\n"
            self.text += text

            # TODO reajust scroll_y after that?
            if len(self.text) > self.max_text_size:
                lines = self.text.splitlines()
                new_lines = lines[
                    int(len(lines) / 4) :
                ]  # Remove the first chunk of lines
                new_text = "\n".join(new_lines) + "\n"
                self.text = new_text

            if is_locked:
                self.scroll_to_bottom()

        finally:
            self._add_text_is_in_progress = False


class LoggingConsole(BoxLayout):
    console_output = ObjectProperty(None)
    """Instance of ConsoleOutput
       :data:`console_output` is an :class:`~kivy.properties.ObjectProperty`
    """

    scroll_view = ObjectProperty(None)
    """Instance of :class:`~kivy.uix.scrollview.ScrollView`
       :data:`scroll_view` is an :class:`~kivy.properties.ObjectProperty`
    """

    foreground_color = ListProperty((1, 1, 1, 1))
    """This defines the color of the text in the console

    :data:`foreground_color` is an :class:`~kivy.properties.ListProperty`,
    Default to '(.5, .5, .5, .93)'
    """

    background_color = ListProperty((0, 0, 0, 1))
    """This defines the color of the background in the console

    :data:`foreground_color` is an :class:`~kivy.properties.ListProperty`,
    Default to '(0, 0, 0, 1)"""

    font_name = StringProperty("data/fonts/Roboto-Regular.ttf")
    """Indicates the font Style used in the console

    :data:`font` is a :class:`~kivy.properties.StringProperty`,
    Default to 'DroidSansMono'
    """

    font_size = NumericProperty("12sp")
    """Indicates the size of the font used for the console

    :data:`font_size` is a :class:`~kivy.properties.NumericProperty`,
    Default to '9'
    """

    def __init__(self, **kwargs):
        super(LoggingConsole, self).__init__(**kwargs)


if __name__ == "__main__":
    runTouchApp(LoggingConsole())
