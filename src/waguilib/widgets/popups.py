from decorator import decorator
from kivy.clock import Clock
from kivymd.toast import toast
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
