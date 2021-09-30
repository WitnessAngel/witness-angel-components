

from kivy.lang import Builder


WIDGET_OUTLINE_HACK = """
<Widget>:
    canvas.after:
        Line:
            rectangle: self.x+1,self.y+1,self.width-1,self.height-1
            dash_offset: 5
            dash_length: 3
"""


def activate_widget_debug_outline():
    """Create a dotted outline around widgets, to help layout setup."""
    Builder.load_string(WIDGET_OUTLINE_HACK)


def load_layout_helper_widgets():
    Builder.load_string("""
    
# Other helpers which might be useful

<Separator@Widget>:
    canvas:
        Color:
            rgba: 1, 1, 1, 0
        Rectangle:
            pos: self.pos
            size: self.size

<VSeparator@Separator>:
    size_hint_y: None
    height: 20

<HSeparator@Separator>:
    size_hint_x: None
    width: 20

    """)


# FIXME use or remove?
#<ConsoleOutput>:
#    readonly: True
#    padding: 6, 6
#    size_hint: (1, None)
