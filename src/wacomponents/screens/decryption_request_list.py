from pathlib import Path
from textwrap import dedent

from jsonrpc_requests import JSONRPCError
from kivy.factory import Factory
from kivy.lang import Builder
from kivy.uix.accordion import Accordion, AccordionItem
from kivymd.app import MDApp
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.list import MDList
from kivymd.uix.screen import Screen
from wacryptolib.jsonrpc_client import JsonRpcProxy, status_slugs_response_error_handler
from wacryptolib.exceptions import ExistenceError

from wacomponents.i18n import tr
from wacomponents.utilities import shorten_uid
from wacomponents.widgets.popups import dialog_with_close_button

Builder.load_file(str(Path(__file__).parent / 'decryption_request_list.kv'))

DESCRIPTION_MIN_LENGTH = 10  # FIXME useless ?


# FIXME RENAME THIS FILE AND KV FILE to decryption_request_visualization.py (and later revelation_request_visualization.py)


class GrowingAccordion(Accordion):  # FIXME move to widgets subpackage!!

    def _do_layout(self, dt):
        children = self.children
        if children:
            all_collapsed = all(x.collapse for x in children)
        else:
            all_collapsed = False

        if all_collapsed:
            children[0].collapse = False

        orientation = self.orientation
        min_space = self.min_space
        min_space_total = len(children) * self.min_space
        w, h = self.size
        x, y = self.pos

        if orientation == 'horizontal':
            children = reversed(children)

        display_space_total = 0
        for child in children:
            if orientation == 'horizontal':
                child_display_space = child.container.children[0].minimum_width
            else:
                child_display_space = child.container.children[0].minimum_height

            child_space = min_space
            child_space += child_display_space * (1 - child.collapse_alpha)

            display_space_total += child_space

            child._min_space = min_space
            child.x = x
            child.y = y
            child.orientation = self.orientation
            if orientation == 'horizontal':
                child.content_size = child_display_space, h
                child.width = child_space
                child.height = h
                x += child_space
            else:
                child.content_size = w, child_display_space
                child.width = w
                child.height = child_space
                y += child_space

        if orientation == 'horizontal':
            self.width = display_space_total
        else:
            self.height = display_space_total


class DecryptionRequestListScreen(Screen):

    def __init__(self, *args, **kwargs):
        self._app = MDApp.get_running_app()
        super().__init__(*args, **kwargs)

    def go_to_previous_screen(self):
        self.manager.current = "CryptainerManagement"

    def _get_gateway_proxy(self):  # FIXME create standalone utility to factorize this, using MDApp.get_running_app()
        jsonrpc_url = self._app.get_wagateway_url()
        gateway_proxy = JsonRpcProxy(
            url=jsonrpc_url, response_error_handler=status_slugs_response_error_handler
        )
        return gateway_proxy

    @staticmethod
    def _list_decryption_request_reformatted(list_decryption_request):  # FIXME both have wrong named, and restructured better than reformatted (which means strings)
        decryption_request_per_cryptainer = {}

        for decryption_request in list_decryption_request:

            decryption_request_per_symkey = {key: value for key, value in decryption_request.items() if
                                             key != 'symkeys_decryption'}

            for symkey_decryption in decryption_request["symkeys_decryption"]:
                decryption_request_per_symkey["symkey_decryption"] = symkey_decryption

                cryptainer_uid = symkey_decryption["cryptainer_uid"]
                _decryption_request_per_cryptainer = decryption_request_per_cryptainer.setdefault(cryptainer_uid, [])
                _decryption_request_per_cryptainer.append(decryption_request_per_symkey)

        return decryption_request_per_cryptainer

    def display_decryption_request_list(self):
        self.ids.list_decryption_request_scrollview.clear_widgets()
        gateway_proxy = self._get_gateway_proxy()

        wa_device_uid = self._app.get_wa_device_uid()
        requester_uid = wa_device_uid["wa_device_uid"]

        try:
            list_decryption_requests = gateway_proxy.list_wadevice_decryption_requests(requester_uid)

        except(JSONRPCError, OSError):
            display_layout = Factory.WABigInformationBox()
            display_layout.ids.inner_label.text = tr._(
                "Error calling method, check the server url")  # FIXME simplify this
            self.ids.list_decryption_request_scrollview.add_widget(display_layout)
            return

        except ExistenceError:
            display_layout = Factory.WABigInformationBox()
            display_layout.ids.inner_label.text = tr._("Aucune demande de déchiffrement")  # FIXME simplify this
            self.ids.list_decryption_request_scrollview.add_widget(display_layout)
            return

        decryption_requests_per_cryptainer = self._list_decryption_request_reformatted(list_decryption_requests)

        display_layout = GrowingAccordion(orientation='vertical', size_hint=(1, None))

        for decryption_request_per_cryptainer in decryption_requests_per_cryptainer.items():

            container_item = Factory.ContainerItem(title='Cryptainer: %s ' % decryption_request_per_cryptainer[0])

            for decryption_request in decryption_request_per_cryptainer[1]:
                _displayed_values = dict(
                    decryption_request_uid=decryption_request["decryption_request_uid"],
                    description=decryption_request["description"],
                    authenticator=decryption_request["public_authenticator"]["keystore_owner"],
                    request_status=decryption_request["request_status"],
                    response_keychain_uid=decryption_request["response_keychain_uid"],
                    response_key_algo=decryption_request["response_key_algo"],
                    decryption_status=decryption_request["symkey_decryption"]["decryption_status"],
                    key_algo=decryption_request["symkey_decryption"]["authenticator_public_key"]["key_algo"],
                    keychain_uid=decryption_request["symkey_decryption"]["authenticator_public_key"]["keychain_uid"],
                )

                # FIXME retranslate all these text blocks, using update_i18n.sh
                decryption_request_summary_text = dedent(tr._("""\
                                                           Decryption request uid: {decryption_request_uid}
                                                           Description: {description}
                                                           Authenticator: {authenticator}, {keychain_uid}({key_algo})
                                                           Request status: {request_status}
                                                           Response key: {response_keychain_uid}({response_key_algo})
                                                           Decryption status: {decryption_status}
                                                       """)).format(**_displayed_values)

                decryption_request_entry = Factory.WAIconListItemEntry(text="Decryption request uid: %s, Status: %s" % (
                    shorten_uid(decryption_request["decryption_request_uid"]), decryption_request["request_status"]))

                def information_callback(widget, decryption_request_info=decryption_request_summary_text):
                    self.show_decryption_request_info(decryption_request_info=decryption_request_info)

                information_icon = decryption_request_entry.ids.information_icon
                information_icon.bind(on_press=information_callback)

                container_item.decryption_requests_list.add_widget(decryption_request_entry)

            display_layout.add_widget(container_item)
        self.ids.list_decryption_request_scrollview.add_widget(display_layout)

    def show_decryption_request_info(self, decryption_request_info):
        dialog_with_close_button(
            close_btn_label=tr._("Close"),
            title=tr._("Decryption Request Summary"),
            text=decryption_request_info,
        )