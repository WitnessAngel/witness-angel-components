from copy import deepcopy
from pathlib import Path
from uuid import UUID

from jsonrpc_requests import JSONRPCError
from kivy.lang import Builder
from kivy.logger import Logger as logger
from kivy.properties import ObjectProperty, BooleanProperty
from kivymd.app import MDApp
from kivymd.uix.screen import Screen

from wacomponents.i18n import tr
from wacomponents.screens.authenticator_management import shorten_uid
from wacomponents.screens.base import WAScreenName
from wacomponents.utilities import format_authenticator_label, COLON, LINEBREAK, indent_text
from wacomponents.widgets.popups import help_text_popup, display_info_toast, \
    safe_catch_unhandled_exception_and_display_popup
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
        self.manager.current = WAScreenName.authenticator_management

    def _query_remote_authenticator_status(self, keystore_uid: UUID):  # Fixme rename?

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
            'public_keys': local_keys_status
        }
        if 'keystore_creation_datetime' in authenticator_metadata:
            local_keys_and_authenticator_metadata["keystore_creation_datetime"] = authenticator_metadata[
                "keystore_creation_datetime"]
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


    def get_remote_public_authenticator_status(self):
        remote_public_authenticator = None
        local_metadata = self._query_local_authenticator_status()
        keystore_uid = local_metadata["keystore_uid"]
        keystore_owner = local_metadata["keystore_owner"]
        msg=""

        try:
            remote_public_authenticator = self._query_remote_authenticator_status(
                keystore_uid=local_metadata["keystore_uid"])
        except(JSONRPCError, OSError) as exc:
            logger.error("Error calling gateway server: %r", exc)
            msg = tr._("Error querying gateway server, please check its url")

        return  remote_public_authenticator, msg # Do not touch anything of the GUI

    @safe_catch_unhandled_exception_and_display_popup
    def refresh_synchronization_status(self):

        local_metadata = self._query_local_authenticator_status()
        keystore_uid = local_metadata["keystore_uid"]
        keystore_owner = local_metadata["keystore_owner"]

        def resultat_callable(result, *args, **kwargs): # FIXME CHANGE THIS NAME

            self.enable_publish_button = enable_publish_button = False  # Defensive setup

            remote_public_authenticator, message = result
            if message:
                self.ids.synchronization_information.text = tr._("No information available")
                display_info_toast(message)
                return

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

                    exceeding_keys_in_remote = (", ".join(exceeding_public_keys_shortened) or "-"),
                    missing_keys_in_remote = (", ".join(missing_public_keys_shortened) or "-"),

                    synchronization_details_text = tr._("Error details") + COLON + LINEBREAK + \
                                                   indent_text(tr._("Exceeding key(s) in remote") + COLON + str(exceeding_keys_in_remote)) + LINEBREAK + \
                                                   indent_text(tr._("Missing key(s) in remote") + COLON + str(missing_keys_in_remote))

            _displayed_values = dict(
                gateway=self._app.get_wagateway_url(),
                status=synchronization_status,
                message=message,
                authenticator_owner=keystore_owner,
                authenticator_uid=str(keystore_uid)
            )
            synchronization_info_text = tr._("Gateway") + COLON + _displayed_values["gateway"] + LINEBREAK + LINEBREAK + \
                                        tr._("Remote status") + COLON + _displayed_values["status"] + LINEBREAK + \
                                        tr._("Message") + COLON + _displayed_values["message"] + LINEBREAK + LINEBREAK + \
                                        tr._("Authenticator owner") + COLON + _displayed_values["authenticator_owner"] + LINEBREAK + \
                                        tr._("Authenticator ID") + COLON + _displayed_values["authenticator_uid"]

            if is_published:
                synchronization_info_text += LINEBREAK + tr._(
                    "Provide this ID to users wanting to rely on you as a Key Guardian") + LINEBREAK

            if synchronization_details_text:
                synchronization_info_text += "\n" + synchronization_details_text

            # Update the GUI

            self.ids.synchronization_information.text = synchronization_info_text
            display_info_toast(tr._("Remote authenticator status has been updated"))

            self.enable_publish_button = enable_publish_button

        self._app._offload_task_with_spinner(self.get_remote_public_authenticator_status, resultat_callable)

    def set_public_authenticator(self):
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
        local_authenticator = deepcopy(local_metadata)
        local_authenticator["public_keys"] = public_keys
        self.gateway_proxy.set_public_authenticator(**local_authenticator)
        return True

    @safe_catch_unhandled_exception_and_display_popup
    def publish_authenticator(self):

        def resultat_callable(result, *args, **kwargs):  # FIXME CHANGE THIS NAME
            self.refresh_synchronization_status()

        self._app._offload_task_with_spinner(self.set_public_authenticator, resultat_callable)

    def display_help_popup(self):

        help_text_popup(
            title=tr._("Authenticator publishing"),
            text=AUTHENTICATOR_PUBLICATION_HELP_PAGE, )

AUTHENTICATOR_PUBLICATION_HELP_PAGE = tr._(
                                         """This page allows to publish the PUBLIC part of an authenticator to a remote Witness Angel Gateway, so that other users may import it to secure their recordings.""") + LINEBREAK * 2 + \
                                     tr._(
                                         """For now, a published authenticator can't be modified or deleted.""") + LINEBREAK * 2 + \
                                     tr._(
                                         """In case of incoherences between the keys locally and remotely stored, errors are displayed here.""")