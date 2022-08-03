
from pathlib import Path
from textwrap import dedent
from uuid import UUID

from jsonrpc_requests import JSONRPCError
from kivy.lang import Builder
from kivy.logger import Logger as logger
from kivy.properties import ObjectProperty, BooleanProperty
from kivymd.app import MDApp
from kivymd.uix.screen import Screen

from wacomponents.i18n import tr
from wacomponents.screens.authenticator_management import shorten_uid
from wacomponents.utilities import format_authenticator_label
from wacomponents.widgets.popups import help_text_popup, display_info_toast, safe_catch_unhandled_exception_and_display_popup
from wacryptolib.exceptions import ExistenceError
from wacryptolib.keystore import load_keystore_metadata, ReadonlyFilesystemKeystore

Builder.load_file(str(Path(__file__).parent / 'authenticator_publication_form.kv'))


class AuthenticatorPublicationFormScreen(Screen):

    selected_authenticator_dir = ObjectProperty(None, allownone=True)

    enable_publish_button = BooleanProperty(False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._app = MDApp.get_running_app()
        self.gateway_proxy = self._app.get_gateway_proxy()

    def go_to_home_screen(self):  # Fixme deduplicate and push to App!
        self.manager.current = "authenticator_selector_screen"

    def _query_remote_authenticator_status(self, keystore_uid: UUID):  #Fixme rename?

        try:
            remote_public_authenticator = self.gateway_proxy.get_public_authenticator(keystore_uid=keystore_uid)

        except ExistenceError:
            remote_public_authenticator = None

        return remote_public_authenticator

    def _query_local_authenticator_status(self):
        authenticator_path = self.selected_authenticator_dir

        # FIXME use export_keystore_tree() asap!
        authenticator_metadata = load_keystore_metadata(authenticator_path)
        readonly_filesystem_keystorage = ReadonlyFilesystemKeystore(authenticator_path)
        local_keys_status = readonly_filesystem_keystorage.list_keypair_identifiers()

        for x in local_keys_status:
            del x["private_key_present"]

        local_keys_and_authenticator_metadata = {
            'keystore_owner': authenticator_metadata["keystore_owner"],
            'keystore_uid': authenticator_metadata["keystore_uid"],
            'keystore_secret': authenticator_metadata["keystore_secret"],  # Only useful when PUBLISHING
            'keystore_creation_datetime':authenticator_metadata["keystore_creation_datetime"],
            'public_keys': local_keys_status
        }
        return local_keys_and_authenticator_metadata

    @staticmethod
    def _compare_local_and_remote_status(local_metadata, remote_public_authenticator) -> dict:

        local_key_tuples = [(public_key["keychain_uid"], public_key["key_algo"]) for public_key in
                            local_metadata["public_keys"]]

        remote_key_tuples = [(public_key["keychain_uid"], public_key["key_algo"]) for public_key in
                             remote_public_authenticator["public_keys"]]

        missing_public_keys_in_remote = set(local_key_tuples) - set(remote_key_tuples)
        exceeding_public_keys_in_remote = set(remote_key_tuples) - set(local_key_tuples)

        is_synchronized = not missing_public_keys_in_remote and not exceeding_public_keys_in_remote

        report = dict(
            missing_keys_in_remote=missing_public_keys_in_remote,
            exceeding_keys_in_remote=exceeding_public_keys_in_remote,
            is_synchronized=is_synchronized)

        return report

    @safe_catch_unhandled_exception_and_display_popup
    def refresh_synchronization_status(self):
        self.enable_publish_button = enable_publish_button = False  # Defensive setup

        local_metadata = self._query_local_authenticator_status()
        keystore_uid = local_metadata["keystore_uid"]
        keystore_owner = local_metadata["keystore_owner"]

        try:
            remote_public_authenticator = self._query_remote_authenticator_status(
                keystore_uid=local_metadata["keystore_uid"])

        except(JSONRPCError, OSError) as exc:
            logger.error("Error calling gateway server: %r", exc)
            msg = tr._("Error querying gateway server, please check its url")
            display_info_toast(msg)
            return  # Do not touch anything of the GUI

        synchronization_details_text = ""

        if remote_public_authenticator is None:
            is_published = False
            synchronization_status = tr._("NOT PUBLISHED")
            message = tr._("The local authenticator does not exist in the remote repository.")
            enable_publish_button = True

        else:

            is_published = True
            synchronization_status = tr._("PUBLISHED")

            report = self._compare_local_and_remote_status(
                local_metadata=local_metadata, remote_public_authenticator=remote_public_authenticator)

            if report["is_synchronized"]:
                message = tr._("The remote authenticator is up to date.")

            else:
                message = tr._("An inconsistency has been detected between the local and remote authenticator.")

                exceeding_public_keys_shortened = [shorten_uid(k[0]) for k in report["exceeding_keys_in_remote"]]
                missing_public_keys_shortened = [shorten_uid(k[0]) for k in report["missing_keys_in_remote"]]

                publication_details = dict(
                    exceeding_keys_in_remote=(", ".join(exceeding_public_keys_shortened) or "-"),
                    missing_keys_in_remote=(", ".join(missing_public_keys_shortened) or "-"),
                )

                synchronization_details_text = dedent(tr._("""\
                      Error details:
                           Exceeding key(s) in remote: {exceeding_keys_in_remote}
                           Missing key(s) in remote: {missing_keys_in_remote}
                  """)).format(**publication_details)

        authenticator_label = format_authenticator_label(authenticator_owner=keystore_owner,
                                                         keystore_uid=keystore_uid, short_uid=False)
        _displayed_values = dict(
            gateway=self._app.get_wagateway_url(),
            status=synchronization_status,
            message=message,
            authenticator_label=authenticator_label,
        )

        synchronization_info_text = dedent(tr._("""\
                        Gateway: {gateway}
                        Remote status: {status}
                        Message: {message}
                        
                        Authenticator : {authenticator_label}
                    """)).format(**_displayed_values)

        if is_published:
            synchronization_info_text += tr._("Provide this ID to users wanting to rely on you as a Key Guardian") + "\n"

        if synchronization_details_text:
            synchronization_info_text += "\n" + synchronization_details_text

        # Update the GUI

        self.ids.synchronization_information.text = synchronization_info_text
        display_info_toast(tr._("Remote authenticator status has been updated"))

        self.enable_publish_button = enable_publish_button

    @safe_catch_unhandled_exception_and_display_popup
    def publish_authenticator(self):

        local_metadata = self._query_local_authenticator_status()

        authenticator_path = self.selected_authenticator_dir
        readonly_filesystem_keystorage = ReadonlyFilesystemKeystore(authenticator_path)
        public_keys = []

        for public_key in local_metadata["public_keys"]:
            public_keys.append({
                "keychain_uid": public_key["keychain_uid"],
                "key_algo": public_key["key_algo"],
                "key_value": readonly_filesystem_keystorage.get_public_key(
                    keychain_uid=public_key["keychain_uid"], key_algo=public_key["key_algo"])
            })

        self.gateway_proxy.set_public_authenticator(keystore_owner=local_metadata["keystore_owner"],
                                                    keystore_uid=local_metadata["keystore_uid"],
                                                    keystore_secret=local_metadata["keystore_secret"],
                                                    keystore_creation_datetime=local_metadata["keystore_creation_datetime"],
                                                    public_keys=public_keys)

        self.refresh_synchronization_status()

    def display_help_popup(self):
        help_text = dedent(tr._("""\
        This page allows to publish the PUBLIC part of an authenticator to a remote Witness Angel Gateway, so that other users may import it to secure their recordings.
        
        For now, a published authenticator can't be modified or deleted.
        
        In case of incoherences between the keys locally and remotely stored, errors are displayed here.
        """))
        help_text_popup(
            title=tr._("Authenticator publishing"),
            text=help_text, )