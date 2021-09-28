from decorator import decorator
from kivy.clock import Clock
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


def dialog_with_close_button(buttons=None, close_btn_label=None, close_btn_callback=None, **kwargs):
    """A dialog which can close itself and works on on smartphone too"""
    close_btn_label = close_btn_label or tr._("Close")
    dialog = None
    def default_on_close(*args):
        dialog.dismiss()
    close_btn_callback = close_btn_callback or default_on_close
    close_btn = MDFlatButton(text=close_btn_label, on_release=close_btn_callback)
    dialog = MDDialog(
                auto_dismiss=False,  # IMPORTANT, else buggy on Android
                buttons=buttons + [close_btn] if buttons else [close_btn],
                **kwargs,
            )
    return dialog
