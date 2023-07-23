from typing import List, Dict, Any
from uuid import UUID

from kivymd.app import MDApp
from kivy.lang import Builder
from kivymd.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.label import Label
from kivy.properties import BooleanProperty
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior

from wacomponents.i18n import tr
from wacomponents.widgets.popups import dialog_with_close_button

Builder.load_string(
    """
<SelectableLabel>:
    # Draw a background to indicate selection
    canvas.before:
        Color:
            rgba: (.0, 0.9, .1, .3) if self.selected else (0, 0, 0, 1)
        Rectangle:
            pos: self.pos
            size: self.size
<RV>:
    viewclass: 'SelectableLabel'
    SelectableRecycleBoxLayout:
        default_size: None, dp(56)
        default_size_hint: 1, None
        size_hint_y: None
        height: self.minimum_height
        orientation: 'vertical'
        multiselect: True
        touch_multiselect: True
"""
)


class SelectableRecycleBoxLayout(
    FocusBehavior, LayoutSelectionBehavior, RecycleBoxLayout
):
    """Adds selection and focus behaviour to the view."""


class SelectableLabel(RecycleDataViewBehavior, Label):
    """Add selection support to the Label"""

    index = None
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)

    def refresh_view_attrs(self, rv, index, data):
        """Catch and handle the view changes"""
        self.index = index
        return super(SelectableLabel, self).refresh_view_attrs(rv, index, data)

    def on_touch_down(self, touch):
        """Add selection on touch down"""
        if super(SelectableLabel, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, rv, index, is_selected):
        """Respond to the selection of items in the view."""
        self.selected = is_selected

        
        if is_selected:
            print("selection changed to {0}".format(rv.data[index]))
            dialog_with_close_button(
                close_btn_label="close moi", title="hello", text="world",
            )
        else:
            print("selection removed for {0}".format(rv.data[index]))


class RV(RecycleView):
    def __init__(self, **kwargs):
        super(RV, self).__init__(**kwargs)
        from wacryptolib.utilities import load_from_json_file
        self.api_response: List[Dict[str, Any]] = load_from_json_file(
            "api.json"
        )
        self.data = self.parse_data()

    def parse_data(self) -> List[Dict[str, str]]:
        parsed: List[Dict[str, str]] = []
        for item in self.api_response:
            cryptainer_name: str = item["symkey_decryption_requests"][0][
                "cryptainer_name"
            ]
            cryptainer_uuid: UUID = item["symkey_decryption_requests"][0][
                "cryptainer_uid"
            ]
            parsed.append({"text": f"{cryptainer_name} ID({cryptainer_uuid})"})
        return parsed


class TestApp(MDApp):
    def build(self):
        return RV()


if __name__ == "__main__":
    TestApp().run()
