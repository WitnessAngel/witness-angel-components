import textwrap
from pathlib import Path

from kivy.lang import Builder


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
