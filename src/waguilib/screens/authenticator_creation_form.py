
from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path
from textwrap import dedent

from functools import partial
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import ObjectProperty, StringProperty
from kivymd.app import MDApp
from kivymd.uix.screen import Screen

from waguilib.widgets.popups import dialog_with_close_button, process_method_with_gui_spinner, register_current_dialog, \
    close_current_dialog, help_text_popup
from wacryptolib.authenticator import initialize_authenticator
from wacryptolib.keygen import generate_keypair
from wacryptolib.keystore import FilesystemKeystore
from wacryptolib.utilities import generate_uuid0

from waguilib.i18n import tr


Builder.load_file(str(Path(__file__).parent / 'authenticator_creation_form.kv'))


THREAD_POOL_EXECUTOR = ThreadPoolExecutor(
    max_workers=1, thread_name_prefix="authenticator_keygen_worker"  # SINGLE worker for now, to avoid concurrency
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
        self.manager.current = "authenticator_selector_screen"

    def reset_initialization_form(self):
        self.set_form_fields_status(enabled=True)
        self.ids.button_initialize.disabled = False
        self.operation_status = ""
        self._do_update_progress_bar(0)
        self.ids.initialization_form_toolbar.disabled = False

    def get_form_values(self):
        return dict(keystore_owner=self.ids.formfield_username.text.strip(),
                    keystore_passphrase=self.ids.formfield_passphrase.text.strip(),
                    keystore_passphrase_hint=self.ids.formfield_passphrasehint.text.strip())

    def validate_form_values(self, form_values):
        form_error = None
        if not all(form_values.values()):
            form_error = tr._("Please enter a username, passphrase and passphrase hint.")
        elif len(form_values["keystore_passphrase"]) < PASSPHRASE_MIN_LENGTH:
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

    def open_dialog(self, text, title, on_dismiss=None):
        dialog_with_close_button(
            title=title,
            text=text,
            **({"on_dismiss": on_dismiss} if on_dismiss else {})
        )

    # No safe_catch_unhandled_exception_and_display_popup() here, we handle finalization in any case
    @process_method_with_gui_spinner
    def _offloaded_initialize_authenticator(self, form_values, authenticator_path):
        success = False

        try:
      
            Clock.schedule_once(partial(self._do_update_progress_bar, 10))

            initialize_authenticator(authenticator_path,
                                     keystore_owner=form_values["keystore_owner"],
                                     extra_metadata=dict(keystore_passphrase_hint=form_values["keystore_passphrase_hint"]))

            filesystem_keystore = FilesystemKeystore(authenticator_path)

            for i in range(1, GENERATED_KEYS_COUNT+1):
                # TODO add some logging here
                key_pair = generate_keypair(
                    key_algo="RSA_OAEP",
                    passphrase=form_values["keystore_passphrase"]
                )
                filesystem_keystore.set_keys(
                    keychain_uid=generate_uuid0(),
                    key_algo="RSA_OAEP",
                    public_key=key_pair["public_key"],
                    private_key=key_pair["private_key"],
                )

                Clock.schedule_once(partial(self._do_update_progress_bar, 10 + int (i * 90 / GENERATED_KEYS_COUNT)))

            success = True

        except Exception as exc:
            print(">> ERROR IN _offloaded_initialize_authenticator THREAD", exc)  # FIXME add logging AND snackbar

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

        if not authenticator_path.is_dir():
            authenticator_path.mkdir(parents=False)  # Only 1 level of folder can be created here!
        assert authenticator_path and authenticator_path.is_dir(), authenticator_path

        self.ids.button_initialize.disabled = True
        self.ids.formfield_passphrase.text = "***"  # PRIVACY
        self.operation_status = tr._("Please wait, initialization might take a few minutes.")

        self.set_form_fields_status(enabled=False)
        self.ids.initialization_form_toolbar.disabled = True

        THREAD_POOL_EXECUTOR.submit(self._offloaded_initialize_authenticator,
                                    form_values=form_values,
                                    authenticator_path=authenticator_path)

    def finish_initialization(self, *args, success, **kwargs):
        if success:
            self.open_dialog(tr._("Initialization successfully completed."),
                             title=tr._("Success"), on_dismiss=lambda x: self.go_to_home_screen())
        else:
            self.open_dialog(tr._("Operation failed, check logs."),
                             title=tr._("Failure"), on_dismiss=lambda x: self.go_to_home_screen())

    def display_help_popup(self):
        help_text = dedent(tr._("""\
        On this page, you can initialize an authenticator inside an empty folder; this authenticator actually consists in metadata files as well as a set of asymmetric keypairs.
        
        To proceed, you have to input your user name or pseudo, a long passphrase (e.g. consisting of 4 different words), and a public hint to help your remember your passphrase later.
        
        You should keep your passphrase somewhere safe (in a digital password manager, on a paper in a vault...), because if you forget any of its aspects (upper/lower case, accents, spaces...), there is no way to recover it.
        """))
        help_text_popup(
            title=tr._("Authenticator creation page"),
            text=help_text,)


