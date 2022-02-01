
from pathlib import Path
from textwrap import dedent

from uuid import UUID

from jsonrpc_requests import JSONRPCError
from kivy.lang import Builder
from kivy.properties import ObjectProperty, StringProperty, BooleanProperty
from kivymd.app import MDApp
from kivymd.uix.screen import Screen
from kivy.logger import Logger as logger

from wacomponents.logging.handlers import safe_catch_unhandled_exception
from wacryptolib.exceptions import ExistenceError
from wacryptolib.jsonrpc_client import JsonRpcProxy, status_slugs_response_error_handler
from wacryptolib.keystore import load_keystore_metadata, ReadonlyFilesystemKeystore

from wacomponents.screens.authenticator_management import shorten_uid
from wacomponents.widgets.popups import help_text_popup, display_info_toast

from wacomponents.i18n import tr


Builder.load_file(str(Path(__file__).parent / 'authenticator_synchronization_form.kv'))


class AuthenticatorSynchronizationScreen(Screen):

    selected_authenticator_dir = ObjectProperty(None, allownone=True)

    enable_publish_button = BooleanProperty(False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._app = MDApp.get_running_app()

    def go_to_home_screen(self):  # Fixme deduplicate and push to App!
        self.manager.current = "authenticator_selector_screen"

    def _get_gateway_proxy(self):

        jsonrpc_url = self._app.get_witness_angel_gateway_url()

        gateway_proxy = JsonRpcProxy(
            url=jsonrpc_url, response_error_handler=status_slugs_response_error_handler
        )
        return gateway_proxy

    def _query_remote_authenticator_status(self, keystore_uid: UUID):

        gateway_proxy = self._get_gateway_proxy()

        try:
            public_authenticator = gateway_proxy.get_public_authenticator_view(keystore_uid=keystore_uid)
            remote_metadata = {  # FIXME simplify
                'keystore_owner': public_authenticator['keystore_owner'],
                'keystore_uid': public_authenticator['keystore_uid'],
                'public_keys': public_authenticator['public_keys'],
            }
        except ExistenceError:
            remote_metadata = None

        return remote_metadata

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
        return local_keys_and_authenticator_metadata

    @staticmethod
    def _compare_local_and_remote_status(local_metadata, remote_metadata) -> dict:

        local_key_tuples = [(public_key["keychain_uid"], public_key["key_algo"]) for public_key in
                            local_metadata["public_keys"]]

        remote_key_tuples = [(public_key["keychain_uid"], public_key["key_algo"]) for public_key in
                             remote_metadata["public_keys"]]

        missing_public_keys_in_remote = set(local_key_tuples) - set(remote_key_tuples)
        exceeding_public_keys_in_remote = set(remote_key_tuples) - set(local_key_tuples)

        is_synchronized = not missing_public_keys_in_remote and not exceeding_public_keys_in_remote

        report = dict(
            missing_keys_in_remote=missing_public_keys_in_remote,
            exceeding_keys_in_remote=exceeding_public_keys_in_remote,
            is_synchronized=is_synchronized)

        return report


    @safe_catch_unhandled_exception
    def refresh_synchronization_status(self):

        self.enable_publish_button = enable_publish_button = False  # Preventive setup

        local_metadata = self._query_local_authenticator_status()

        try:
            remote_metadata = self._query_remote_authenticator_status(
                keystore_uid=local_metadata["keystore_uid"])
        except(JSONRPCError, OSError) as exc:
            logger.error("Error calling gateway server: %r", exc)
            msg = tr._("Error querying gateway server, please check its url")
            display_info_toast(msg)
            return  # Do not touch anything of the GUI

        synchronization_details_text = None

        if remote_metadata is None:
            synchronization_status = tr._("NOT PUBLISHED")
            message = tr._("The local authenticator does not exist in the remote repository.")
            enable_publish_button = True

        else:

            synchronization_status = tr._("PUBLISHED")

            report = self._compare_local_and_remote_status(
                local_metadata=local_metadata, remote_metadata=remote_metadata)

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

                synchronization_details_text = tr._(dedent("""\
                      Error details:
                           Exceeding key(s) in remote: {exceeding_keys_in_remote}
                           Missing key(s) in remote: {missing_keys_in_remote}
                  """)).format(**publication_details)

        _displayed_values = dict(
            gateway="https://witnessangel.com/",
            status=synchronization_status,
            message=message,
        )

        synchronization_info_text = dedent(tr._("""\
                        Gateway : {gateway}
                        Remote status : {status}
                        Message : {message}
                    """)).format(**_displayed_values)

        # Update the GUI

        self.ids.synchronization_information.text = synchronization_info_text
        self.ids.publication_details.text = synchronization_details_text or ""
        display_info_toast(tr._("Remote authenticator status has been updated"))

        self.enable_publish_button = enable_publish_button


    #def refresh_status(self):
        #self._refresh_synchronization_status()
        #self.manager.current = "authenticator_synchronization_screen"


    @safe_catch_unhandled_exception
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

        '''
        if self.report["missing_keys_in_remote"]:  # FIXME not a good idea?
            authenticator_path = self.selected_authenticator_dir
            readonly_filesystem_keystorage = ReadonlyFilesystemKeystore(authenticator_path)
            authenticator_metadata = load_keystore_metadata(authenticator_path)
            for missing_key in self.report["missing_keys_in_remote"]:
                public_keys.append({
                    "keychain_uid": missing_key[0],
                    "key_algo": missing_key[1],
                    "key_value": readonly_filesystem_keystorage.get_public_key(keychain_uid= missing_key[0], key_algo=missing_key[1])
                })'''

        gateway_proxy = self._get_gateway_proxy()
        gateway_proxy.set_public_authenticator_view(keystore_owner=local_metadata["keystore_owner"],
                                                            keystore_uid=local_metadata["keystore_uid"],
                                                            keystore_secret=local_metadata["keystore_secret"],
                                                            public_keys=public_keys)

        self.refresh_synchronization_status()


    def display_help_popup(self):
        help_text = dedent(tr._("""\
        TODO
        """))
        help_text_popup(
            title=tr._("Authenticator publishing"),
            text=help_text, )
