import logging

from decorator import decorator
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.uix.modalview import ModalView
from kivymd.app import MDApp
from kivymd.toast import toast
from kivymd.uix.button import MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.snackbar import Snackbar

from wacomponents.default_settings import IS_ANDROID
from wacomponents.i18n import tr
from wacomponents.logging.handlers import safe_catch_unhandled_exception

logger = logging.getLogger(__name__)


def display_info_toast(message):
    """Small temporary popup"""
    toast_options = {"duration": 1.5}
    if IS_ANDROID:
        toast_options = {"length_long": False}
    # Exact signature is different on Android and Desktop!
    logger.debug("Displaying Toast with message %r", message)
    toast(message, **toast_options)


def display_info_snackbar(message, duration=3.5):
    """Full-width temporary bottom message bar"""
    logger.debug("Displaying Snackbar with message %r", message)
    Snackbar(
        text=message,
        font_size="12sp",
        duration=duration,
        # button_text="BUTTON",
        # button_callback=app.callback
    ).open()


@decorator
def display_snackbar_on_error(f, *args, **kwargs):
    try:
        return f(*args, **kwargs)
    except Exception as exc:
        message = tr._("Abnormal error caught: %s") % exc.__class__.__name__
        displayer = lambda dt: display_info_snackbar(message=message)
        Clock.schedule_once(displayer, 0)  # Scheduled so that other threads can display popups too
        raise  # Let it flow, other decorator shall intercept it


def safe_catch_unhandled_exception_and_display_popup(func):
    return safe_catch_unhandled_exception(display_snackbar_on_error(func))


def dialog_with_close_button(
    buttons=None, close_btn_label=None, full_width=False, close_btn_callback=None, auto_open_and_register=True, **kwargs
):
    """A dialog which can close itself and works on smartphone too"""
    close_btn_label = close_btn_label or tr._("Close")
    logger.debug("Displaying dialog with close button %r", close_btn_label)
    dialog = None

    def default_on_close(*args):
        dialog.dismiss()

    close_btn_callback = close_btn_callback or default_on_close
    close_btn = MDFlatButton(text=close_btn_label, on_release=close_btn_callback)
    if full_width:
        kwargs["size_hint_x"] = 0.95
        kwargs["size_hint_y"] = None
    dialog = MDDialog(
        auto_dismiss=False,  # IMPORTANT, else buggy on Android
        buttons=buttons + [close_btn] if buttons else [close_btn],
        **kwargs,
    )

    if auto_open_and_register:
        dialog.open()
        register_current_dialog(dialog)

    return dialog


def help_text_popup(title, text):  # FIXME rename this
    text = "[size=13sp]" + text + "[/size]"  # Else it's too big
    dialog_with_close_button(title=tr._(title), text=text, full_width=True)


_CURRENT_DIALOG = None  # System to avoid nasty bugs with multiple dialogs overwriting each other's variables


def register_current_dialog(dialog):
    # Works for MDFileManager as well as normal ModalView
    global _CURRENT_DIALOG
    if has_current_dialog():
        return  # Might happen with slow UI, multiple clicks on buttons!
    _CURRENT_DIALOG = dialog


def has_current_dialog():
    global _CURRENT_DIALOG
    if not _CURRENT_DIALOG:
        return False
    if isinstance(_CURRENT_DIALOG, MDFileManager):
        return _CURRENT_DIALOG._window_manager_open  # Wraps a ModalView
    else:
        assert isinstance(_CURRENT_DIALOG, ModalView)
        return bool(_CURRENT_DIALOG._window)


def close_current_dialog():
    global _CURRENT_DIALOG
    if not has_current_dialog():
        return  # Might happen with slow UI, multiple clicks on buttons!
    if isinstance(_CURRENT_DIALOG, MDFileManager):
        _CURRENT_DIALOG.close()  # Wraps a ModalView
    else:
        assert isinstance(_CURRENT_DIALOG, ModalView)
        _CURRENT_DIALOG.dismiss()
    _CURRENT_DIALOG = None


Builder.load_string(
    """

<WaitSpinner@MDSpinner>:
    size_hint: None, None
    size: dp(46), dp(46)
    pos_hint: {'center_x': .5, 'center_y': .5}
    active: False

"""
)


@decorator  # FIXME OBSOLETE - REPLACE THIS WITH GUIAPP._offload_task_with_spinner()
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
