from kivymd.app import MDApp

from waguilib.application._common_runtime_support import WaRuntimeSupportMixin


class WaGenericGui(WaRuntimeSupportMixin, MDApp):
    """
    Base class for standalone KIVY GUI applications, which don't need a client/service functioning.
    """

    def build(self):
        self.theme_cls.primary_palette = "Blue"
        #self.theme_cls.theme_style = "Dark"  # or "Light"
        self.theme_cls.primary_hue = "900"  # "500"

    def on_pause(self):
        # FIXME move this to new base class in WAGUILIB
        return True
