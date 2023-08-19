import logging
from pathlib import Path

from jsonrpc_requests import JSONRPCError
from kivy.factory import Factory
from kivy.lang import Builder
from kivy.properties import ObjectProperty
from kivymd.uix.button import MDFlatButton
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.tab import MDTabsBase

from wacomponents.i18n import tr
from wacomponents.screens.base import WAScreenName, WAScreenBase
from wacomponents.utilities import (
    format_revelation_request_label,
    format_keypair_label,
    format_authenticator_label,
    COLON,
    LINEBREAK,
    format_cryptainer_label,
    shorten_uid,
)
from wacomponents.widgets.layout_components import GrowingAccordion, build_fallback_information_box
from wacomponents.widgets.popups import (
    dialog_with_close_button,
    close_current_dialog,
    display_info_snackbar,
    help_text_popup,
    safe_catch_unhandled_exception_and_display_popup,
    display_info_toast,
)
from wacryptolib.cipher import encrypt_bytestring
from wacryptolib.exceptions import KeyLoadingError, KeyDoesNotExist, KeystoreDoesNotExist, AuthenticationError
from wacryptolib.keygen import load_asymmetric_key_from_pem_bytestring
from wacryptolib.keystore import load_keystore_metadata, FilesystemKeystore
from wacryptolib.trustee import TrusteeApi
from wacryptolib.utilities import load_from_json_bytes, dump_to_json_bytes

Builder.load_file(str(Path(__file__).parent / "authenticator_revelation_request_management.kv"))


logger = logging.getLogger(__name__)


class Tab(MDFloatLayout, MDTabsBase):
    """Class implementing content for a tab as a FloatLayout."""


class SymkeyDecryptionStatus:  # BEWARE, DUPLICATED from WASERVER
    DECRYPTED = "DECRYPTED"
    PRIVATE_KEY_MISSING = "PRIVATE_KEY_MISSING"
    CORRUPTED = "CORRUPTED"
    METADATA_MISMATCH = "METADATA_MISMATCH"
    PENDING = "PENDING"


class AuthenticatorRevelationRequestManagementScreen(WAScreenBase):

    selected_authenticator_dir = ObjectProperty(None, allownone=True)


    def go_to_home_screen(self):  # Fixme deduplicate and push to App!
        self.manager.current = WAScreenName.authenticator_management

    def _display_remote_revelation_request_(self, revelation_requests_per_status_list):  # FIXME rename

        logger.debug("Displaying remote decryption requests")

        tab_per_status = dict(
            PENDING=self.ids.decryption_request_pending_table,
            REJECTED=self.ids.decryption_request_rejected_table,
            ACCEPTED=self.ids.decryption_request_accepted_table,
        )

        for status, revelation_requests in revelation_requests_per_status_list.items():
            recycleview_data = []

            revelation_requests.sort(key=lambda request: request["created_at"], reverse=True)
            for revelation_request in revelation_requests:

                revelation_request_label = format_revelation_request_label(
                    revelation_request_uid=revelation_request["revelation_request_uid"],
                    revelation_request_creation_datetime=revelation_request["created_at"],
                    short_uid=False,
                )

                symkey_decryption_request_count = len(revelation_request["symkey_decryption_requests"])
                symkey_decryption_request_count_label = tr._("Symkey decryption requests: %d") % symkey_decryption_request_count

                def _specific_go_to_details_page_callback(status=status, revelation_request=revelation_request):
                    detail_screen = self.manager.get_screen(WAScreenName.authenticator_revelation_request_detail)
                    detail_screen.setup_revelation_request_details(
                        status=status, revelation_request=revelation_request
                    )
                    self.manager.current = WAScreenName.authenticator_revelation_request_detail

                recycleview_data.append({
                        "text": revelation_request_label,
                        "secondary_text": symkey_decryption_request_count_label,
                        "information_callback": _specific_go_to_details_page_callback,
                    })

            if not revelation_requests:
                fallback_info_box = build_fallback_information_box(tr._("No authorization request"))
                # FIXME HANDLE THIS
                ##tab_per_status[status].add_widget(fallback_info_box)
                # DO SOMETHING

            tab_per_status[status].data = recycleview_data

    @staticmethod
    def sort_list_revelation_request_per_status(authenticator_revelation_request_list):
        DECRYPTION_REQUEST_STATUSES = ["PENDING", "ACCEPTED", "REJECTED"]  # KEEP IN SYNC with WASERVER
        revelation_requests_per_status = {status: [] for status in DECRYPTION_REQUEST_STATUSES}

        for revelation_request in authenticator_revelation_request_list:
            revelation_requests_per_status[revelation_request["revelation_request_status"]].append(revelation_request)
        return revelation_requests_per_status

    def _fetch_revelation_requests_sorted_by_status(self):
        authenticator_path = self.selected_authenticator_dir
        revelation_requests_per_status_list = None
        authenticator_metadata = load_keystore_metadata(authenticator_path)
        keystore_uid = authenticator_metadata["keystore_uid"]
        gateway_proxy = self._app.get_gateway_proxy()
        try:
            authenticator_revelation_request_list = gateway_proxy.list_authenticator_revelation_requests(
                authenticator_keystore_secret=authenticator_metadata["keystore_secret"],
                authenticator_keystore_uid=keystore_uid,
            )
            revelation_requests_per_status_list = self.sort_list_revelation_request_per_status(
                authenticator_revelation_request_list
            )
            message = tr._("Authorization requests were updated")

        except KeystoreDoesNotExist:
            message = tr._("Authenticator does not exist in remote registry")

        except AuthenticationError:
            message = tr._("The keystore secret of authenticator is not valid")

        except (JSONRPCError, OSError) as exc:  # FIXME factorize this!
            logger.error("Error calling gateway server: %r", exc)
            message = tr._("Error querying gateway server, please check its url and your connectivity")

        return revelation_requests_per_status_list, message

    @safe_catch_unhandled_exception_and_display_popup
    def fetch_and_display_revelation_requests(self):

        self.ids.tabs.switch_tab(self.ids.tabs.get_tab_list()[0])  # Return to first Tab

        def resultat_callable(result, *args, **kwargs):  # FIXME CHANGE THIS NAME
            revelation_requests_per_status_list, message = result
            if revelation_requests_per_status_list is None:
                display_info_snackbar(message)
            else:
                display_info_toast(message)
                self._display_remote_revelation_request_(
                    revelation_requests_per_status_list=revelation_requests_per_status_list
                )

        self._app._offload_task_with_spinner(self._fetch_revelation_requests_sorted_by_status, resultat_callable)

    def display_help_popup(self):   # FIXME update this
        authenticator_revelation_request_management_help_text = (
            tr._(
                """This page summarizes the authorization requests that have been sent to your authenticator, in order to decrypt some remote containers."""
            )
            + LINEBREAK * 2
            + tr._(
                """Requests can be freely rejected. Else, to accept them, you must input your passphrase, which will be used to load your private keys and generate authorization tokens for the requester."""
            )
            + LINEBREAK * 2
            + tr._(
                """For now, it is not possible to change the status of a request which has been accepted or rejected."""
            )
        )

        help_text_popup(
            title=tr._("Remote authorization requests page"), text=authenticator_revelation_request_management_help_text
        )
