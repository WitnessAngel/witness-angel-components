from decorator import decorator
from kivy.clock import Clock
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.toast import toast
from kivymd.uix.button import MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.snackbar import Snackbar

from waguilib.i18n import tr
from waguilib.logging.handlers import safe_catch_unhandled_exception


def display_info_toast(msg, duration=2.5):
    toast(msg, duration=duration)


@decorator
def display_snackbar_on_error(f, *args, **kwargs):
    try:
        return f(*args, **kwargs)
    except Exception as exc:
        message = tr._("Abnormal error caught: %s") % exc.__class__.__name__
        displayer = lambda dt: Snackbar(text=message).open()
        Clock.schedule_once(displayer, 0)  # Scheduled so that other threads can display popups too
        raise  # Let it flow, other decorator shall intercept it


def safe_catch_unhandled_exception_and_display_popup(func):
    return safe_catch_unhandled_exception(display_snackbar_on_error(func))


def dialog_with_close_button(buttons=None, close_btn_label=None, full_width=False,
                             close_btn_callback=None, **kwargs):
    """A dialog which can close itself and works on on smartphone too"""
    close_btn_label = close_btn_label or tr._("Close")
    dialog = None
    def default_on_close(*args):
        dialog.dismiss()
    close_btn_callback = close_btn_callback or default_on_close
    close_btn = MDFlatButton(text=close_btn_label, on_release=close_btn_callback)
    if full_width:
        kwargs["size_hint_x"] = 0.95
    dialog = MDDialog(
                auto_dismiss=False,  # IMPORTANT, else buggy on Android
                buttons=buttons + [close_btn] if buttons else [close_btn],
                **kwargs,
            )
    return dialog


_CURRENT_DIALOG = None  # System to avoid nasty bugs with multiple dialogs overwriting each other's variables

def register_current_dialog(dialog):
    global _CURRENT_DIALOG
    if has_current_dialog():
        raise RuntimeError("Multiple popups can't be opened at the same time")
    _CURRENT_DIALOG = dialog

def has_current_dialog():
    global _CURRENT_DIALOG
    return(_CURRENT_DIALOG and _CURRENT_DIALOG._window)

def close_current_dialog():
    global _CURRENT_DIALOG
    if not has_current_dialog():
        raise RuntimeError("No popups currently open for closing")
    _CURRENT_DIALOG.dismiss()
    _CURRENT_DIALOG = None


Builder.load_string("""

<WaitSpinner@MDSpinner>:
    size_hint: None, None
    size: dp(46), dp(46)
    pos_hint: {'center_x': .5, 'center_y': .5}
    active: False

""")

@decorator
def process_method_with_gui_spinner(func, self, *args, **kwargs):
    """
    Handle a time-consuming operation with the display of a GUI spinner,
    which must have id "wait_spinner" and be located in root tree.

    Can be called from secondary thread too.
    """
    _app = MDApp.get_running_app()
    wait_spinner = _app.root.ids.wait_spinner
    Clock.schedule_once(lambda x: wait_spinner.setter("active")(x, True))
    try:
        return func(self, *args, **kwargs)
    finally:
        Clock.schedule_once(lambda x: wait_spinner.setter("active")(x, False))


