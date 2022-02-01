from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path
from textwrap import dedent

from functools import partial
from uuid import UUID

from jsonrpc_requests import JSONRPCError
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import ObjectProperty, StringProperty
from kivymd.app import MDApp
from kivymd.uix.screen import Screen
from kivy.logger import Logger as logger

from wacomponents.logging.handlers import safe_catch_unhandled_exception
from wacryptolib.exceptions import ExistenceError
from wacryptolib.jsonrpc_client import JsonRpcProxy, status_slugs_response_error_handler
from wacryptolib.keystore import load_keystore_metadata, ReadonlyFilesystemKeystore

from wacomponents.screens.authenticator_management import shorten_uid
from wacomponents.widgets.popups import dialog_with_close_button, process_method_with_gui_spinner, \
    register_current_dialog, \
    close_current_dialog, help_text_popup, display_info_toast

from wacomponents.i18n import tr

import requests

Builder.load_file(str(Path(__file__).parent / 'authenticator_synchronization_form.kv'))

'''
THREAD_POOL_EXECUTOR = ThreadPoolExecutor(
    max_workers=1, thread_name_prefix="authenticator_keygen_worker"  # SINGLE worker for now, to avoid concurrency
)

GENERATED_KEYS_COUNT = 7
PASSPHRASE_MIN_LENGTH = 20


class AuthenticatorDoesNotExist(ExistenceError):  # TODO add this in exceptions.py of cryptolib project
    pass


class AuthenticatorAlreadyExists(ExistenceError):  # TODO add this in exceptions.py of cryptolib project
    pass
'''

class AuthenticatorSynchronizationScreen(Screen):
    selected_authenticator_dir = ObjectProperty(None, allownone=True)

    synchronization_status = StringProperty()
    is_synchronized = ObjectProperty(None, allownone=True)

    report = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._app = MDApp.get_running_app()

    def go_to_home_screen(self):
        self.manager.current = "authenticator_selector_screen"

    def _get_gateway_proxy(self):

        jsonrpc_url = self._app.get_witness_angel_gateway_url()

        gateway_proxy = JsonRpcProxy(
            url=jsonrpc_url, response_error_handler=status_slugs_response_error_handler
        )
        return gateway_proxy

    def _query_remote_athenticator_status(self, keystore_uid: UUID):

        gateway_proxy = self._get_gateway_proxy()

        try:
            public_authenticator = gateway_proxy.get_public_authenticator_view(keystore_uid=keystore_uid)
            is_published = True
            remote_metadata = {
                'keystore_owner': public_authenticator['keystore_owner'],
                'keystore_uid': public_authenticator['keystore_uid'],
                'public_keys': public_authenticator['public_keys'],
            }

        except ExistenceError:
            is_published = False
            remote_metadata = None

        return is_published, remote_metadata

    @staticmethod
    def _compare_local_and_remote_status(local_metadata, remote_metadata) -> dict:

        local_keys_tuple = [(public_key["keychain_uid"], public_key["key_algo"]) for public_key in
                            local_metadata_status["public_keys"]]

        remote_keys_tuple = [(public_key["keychain_uid"], public_key["key_algo"]) for public_key in
                             remote_metadata_status["public_keys"]]

        missing_public_keys_in_remote = set(local_keys_tuple) - set(remote_keys_tuple)
        exceeding_public_keys_in_remote = set(remote_keys_tuple) - set(local_keys_tuple)

        if not missing_public_keys_in_remote and not exceeding_public_keys_in_remote:
            is_synchronized = False

        report = dict(
            missing_keys_in_remote=missing_public_keys_in_remote,
            exceeding_keys_in_remote=exceeding_public_keys_in_remote,
            is_synchronized=is_synchronized)

        return report

    def _refresh_synchronization_status(self):
        self.ids.publication_details.text = ""

        authenticator_path = self.selected_authenticator_dir

        # METHOD _get_local_authenticator_tree()  # mettre FIXME use export_keystore_tree()
        authenticator_metadata = load_keystore_metadata(authenticator_path)
        readonly_filesystem_keystorage = ReadonlyFilesystemKeystore(authenticator_path)
        local_keys_status = readonly_filesystem_keystorage.list_keypair_identifiers()

        for x in local_keys_status:
            del x["private_key_present"]

        local_keys_and_authenticator_metadata_reformatted = {
            'keystore_owner': authenticator_metadata["keystore_owner"],
            'keystore_uid': authenticator_metadata["keystore_uid"],
            'public_keys': local_keys_status
        }

        # METHOD _query_remote_athenticator_status() -> remote_metadata || None

        is_published, remote_metadata= self._query_remote_athenticator_status(
            keystore_uid=authenticator_metadata["keystore_uid"])

        # Body de cette méthod _refresh_synchronization_status():
        # if remote_metadata is None : <cas non publié>
        # else: appeler _compare_local_and_remote_status()
        #       if synchronized : <gérer cas full synchro ok>
        #       else: <afficher détails erreur>

        # Ne mettre à jour la GUI que tout à la fin de cette fonction


        self.report = self._compare_local_and_remote_status(local_keys_and_authenticator_metadata_reformatted, remote_metadata, is_published=is_published)

        is_synchronized = self.report["is_synchronized"]

        exceeding_public_keys_cast = [shorten_uid(k[0]) for k in self.report["exceeding_keys_in_remote"]]
        missing_public_keys_cast = [shorten_uid(k[0]) for k in self.report["missing_keys_in_remote"]]

        if is_synchronized is None:
            synchronization_status = tr._("PUBLISHED")
            message = tr._("An inconsistency has been detected between the local and remote authenticator.")
            publication_details = dict(
                exceeding_keys_in_remote=(", ".join(exceeding_public_keys_cast) or "-"),
                missing_keys_in_remote=(", ".join(missing_public_keys_cast) or "-"),
            )

            publication_details_text = tr._(dedent("""\
                                              Details:
                                                   Exceeding key(s) in remote : {exceeding_keys_in_remote}
                                                   Missing key(s) in remote : {missing_keys_in_remote}
                                          )""")).format(**publication_details)

            self.ids.publication_details.text = publication_details_text

        elif not is_synchronized:
            synchronization_status = tr._("PUBLISHED")
            message = tr._("The remote authenticator is up to date.")

        else:
            synchronization_status = tr._("NOT PUBLISHED")
            message = tr._("The local authenticator does not exist on the remote repository.")

        displayed_values = dict(
            gateway="https://witnessangel.com/",
            status=synchronization_status,
            message=message,
        )

        synchronization_info_text = dedent(tr._("""\
                        Gateway : {gateway}
                        Remote status : {status}
                        Message : {message}
                    """)).format(**displayed_values)

        textarea = self.ids.synchronization_information
        textarea.text = synchronization_info_text

        self.is_synchronized = is_synchronized

        msg = "Publication of authenticators has been updated"
        display_info_toast(msg)

    @safe_catch_unhandled_exception
    def refresh_status(self):
        try:
            self._refresh_status()
            self.manager.current = "authenticator_synchronization_screen"
        except(JSONRPCError, OSError) as exc:
            logger.error("Error calling gateway server: %r", exc)
            msg = tr._("Error querying gateway server, please check its url")
            display_info_toast(msg)

    @safe_catch_unhandled_exception
    def publish_authenticator(self):
        public_keys = []
        if self.report["missing_keys_in_remote"]:  # FIXME not a good idea?
            authenticator_path = self.selected_authenticator_dir
            readonly_filesystem_keystorage = ReadonlyFilesystemKeystore(authenticator_path)
            authenticator_metadata = load_keystore_metadata(authenticator_path)
            for missing_key in self.report["missing_keys_in_remote"]:
                public_keys.append({
                    "keychain_uid": missing_key[0],
                    "key_algo": missing_key[1],
                    "key_value": readonly_filesystem_keystorage.get_public_key(keychain_uid= missing_key[0], key_algo=missing_key[1])
                })

            # tODO fixme
            self.escrow_proxy.set_public_authenticator_view(keystore_owner=authenticator_metadata["keystore_owner"],
                                                            keystore_uid=authenticator_metadata["keystore_uid"],
                                                            keystore_secret=authenticator_metadata[
                                                                "keystore_secret"],
                                                            public_keys=public_keys)

        # tODO fixme
        self.refresh_status()

    def display_help_popup(self):
        help_text = dedent(tr._("""\
        TODO
        """))
        help_text_popup(
            title=tr._("Authenticator publishing"),
            text=help_text, )
