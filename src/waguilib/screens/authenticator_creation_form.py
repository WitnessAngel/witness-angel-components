
from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path
from textwrap import dedent

from functools import partial
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import ObjectProperty, StringProperty
from kivymd.app import MDApp
from kivymd.uix.button import MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.screen import Screen

from wacryptolib.authenticator import initialize_authenticator
from wacryptolib.key_generation import generate_asymmetric_keypair
from wacryptolib.key_storage import FilesystemKeyStorage
from wacryptolib.utilities import generate_uuid0

from wa_keygen_gui import tr


Builder.load_file(str(Path(__file__).parent / 'authenticator_creation_form.kv'))


THREAD_POOL_EXECUTOR = ThreadPoolExecutor(
    max_workers=1, thread_name_prefix="keygen_worker"  # SINGLE worker for now, to avoid concurrency
)

GENERATED_KEYS_COUNT = 7
PASSPHRASE_MIN_LENGTH = 20


class AuthenticatorCreationScreen(Screen):

    _selected_authenticator_path = ObjectProperty(None, allownone=True)

    operation_status = StringProperty()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._app = MDApp.get_running_app()

    def go_to_home_screen(self):
        self.manager.current = "keyring_selector_screen"

    def reset_initialization_form(self):
        self.set_form_fields_status(enabled=True)
        self.ids.button_initialize.disabled = False
        self.operation_status = ""
        self._do_update_progress_bar(0)
        self.ids.initialization_form_toolbar.disabled = False

    def get_form_values(self):
        return dict(user=self.ids.formfield_username.text.strip(),
                    passphrase=self.ids.formfield_passphrase.text.strip(),
                    passphrase_hint=self.ids.formfield_passphrasehint.text.strip())

    def validate_form_values(self, form_values):
        form_error = None
        if not all(form_values.values()):
            form_error = tr._("Please enter a username, passphrase and passphrase hint.")
        elif len(form_values["passphrase"]) < PASSPHRASE_MIN_LENGTH:
            form_error = tr._("Passphrase must be at least %s characters long.") % PASSPHRASE_MIN_LENGTH
        if form_error:
            raise ValueError(form_error)

    def request_authenticator_initialization(self):
        form_values = self.get_form_values()

        try :
            self.validate_form_values(form_values)
        except ValueError as exc:
            self.open_dialog(str(exc), title=tr._("Validation error"))
            return

        self._launch_authenticator_initialization(form_values=form_values)

    def open_dialog(self, text, title, on_release=None):
        on_release = on_release or self.close_dialog
        self._dialog = MDDialog(
            auto_dismiss=False,
            title=title,
            text=text,
            buttons=[MDFlatButton(text="Close", on_release=on_release)],
        )
        self._dialog.open()

    def close_dialog(self, obj):
        self._dialog.dismiss()

    def close_dialog_and_leave(self, obj):
        self.close_dialog(obj)
        self.go_to_home_screen()

    def _offloaded_initialize_authenticator(self, form_values, authenticator_path):
        success = False

        try:

            Clock.schedule_once(partial(self._do_update_progress_bar, 10))

            initialize_authenticator(authenticator_path,
                                     user=form_values["user"],
                                     extra_metadata=dict(passphrase_hint=form_values["passphrase_hint"]))

            filesystem_key_storage = FilesystemKeyStorage(authenticator_path)

            for i in range(1, GENERATED_KEYS_COUNT+1):
                key_pair = generate_asymmetric_keypair(
                    key_type="RSA_OAEP",
                    passphrase=form_values["passphrase"]
                )
                filesystem_key_storage.set_keys(
                    keychain_uid=generate_uuid0(),
                    key_type="RSA_OAEP",
                    public_key=key_pair["public_key"],
                    private_key=key_pair["private_key"],
                )

                Clock.schedule_once(partial(self._do_update_progress_bar, 10 + int (i * 90 / GENERATED_KEYS_COUNT)))

            success = True

        except Exception as exc:
            print(">>>>>>>>>> ERROR IN THREAD", exc)  # FIXME add logging AND snackbar

        Clock.schedule_once(partial(self.finish_initialization, success=success))


    def set_form_fields_status(self, enabled):

        form_ids=self.ids
        form_fields = [
            form_ids.formfield_username,
            form_ids.formfield_passphrase,
            form_ids.formfield_passphrasehint,
        ]

        for text_field in form_fields:
            text_field.focus = False
            text_field.disabled = not enabled
            # Unfocus triggered an animation, we must disable it
            Animation.cancel_all(text_field, "fill_color", "_line_width", "_hint_y", "_hint_lbl_font_size")
            if enabled:
                text_field.text = ""  # RESET

    def update_progress_bar(self, percent):
        Clock.schedule_once(partial(self._do_update_progress_bar, percent))

    def _do_update_progress_bar(self, percent, *args, **kwargs):
        self.ids.progress_bar.value = percent

    def _launch_authenticator_initialization(self, form_values):
        authenticator_path = self._selected_authenticator_path
        assert authenticator_path and authenticator_path.is_dir(), authenticator_path

        self.ids.button_initialize.disabled = True
        self.ids.formfield_passphrase.text = "***"  # PRIVACY
        self.operation_status = tr._("Please wait a few seconds, initialization is in process.")

        self.set_form_fields_status(enabled=False)
        self.ids.initialization_form_toolbar.disabled = True

        THREAD_POOL_EXECUTOR.submit(self._offloaded_initialize_authenticator,
                                    form_values=form_values,
                                    authenticator_path=authenticator_path)

    def finish_initialization(self, *args, success, **kwargs):
        on_release = self.close_dialog_and_leave
        if success:
            self.open_dialog(tr._("Initialization successfully completed."),
                             title=tr._("Success"), on_release=on_release)
        else:
            self.open_dialog(tr._("Operation failed, check logs."),
                             title=tr._("Failure"), on_release=on_release)

    def display_help_popup(self):
        help_text = dedent(tr._("""\
        On this page, you can initialize an authenticator inside an empty folder; this authenticator actually consists in metadata files as well as a set of asymmetric keypairs.
        
        To proceed, you have to input your user name or pseudo, a long passphrase (e.g. consisting of 4 different words), and a public hint to help your remember your passphrase later.
        
        You should keep your passphrase somewhere safe (in a digital password manager, on a paper in a vault...), because if you forget any of its aspects (upper/lower case, accents, spaces...), there is no way to recover it.
        """))
        MDDialog(
            auto_dismiss=True,
            title=tr._("Authenticator creation page"),
            text=help_text,
            ).open()

