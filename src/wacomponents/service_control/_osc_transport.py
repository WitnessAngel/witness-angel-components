import socket
from functools import partial
from pathlib import Path

from kivy.logger import Logger as logger
from kivy.utils import platform
# TODO factorize and use unix socks when possible
from oscpy.client import OSCClient
from oscpy.server import OSCThreadServer as _OSCThreadServer

from wacomponents.default_settings import INTERNAL_APP_ROOT


class RobustOSCThreadServer(_OSCThreadServer):

    def _listen(self):
        while True:  # This server listens forever
            try:
                super()._listen()
            except Exception as exc:
                print(
                    "!!! Unhandled exception intercepted in RobustOSCThreadServer._listen(): %r" % exc
                )


def _osc_default_handler(address, *values, socket_name=None):
    print(
        "Unknown OSC address %s called (arguments %s) on listener %s" % (
            address, list(values), socket_name)
    )


def _get_osc_socket_options(socket_index):
    if platform == "win":
        socket_options = dict(
            address="127.0.0.1", port=6420 + socket_index, family="inet"
        )
    else:
        socket_file = INTERNAL_APP_ROOT.joinpath(".witnessangel%d.sock" % socket_index)
        socket_options = dict(address=str(socket_file), port=None, family="unix")
    return socket_options


def get_osc_server(is_application=True):
    """
    Get the OSC server for the application (GUI) or service (background task)
    """
    socket_name = "application" if is_application else "service"
    socket_index = 0 if is_application else 1
    socket_options = _get_osc_socket_options(socket_index=socket_index)

    server = RobustOSCThreadServer(
        encoding="utf8", default_handler=partial(_osc_default_handler, socket_name=socket_name)
    )  # This launches a DAEMON thread!

    def starter_callback():
        logger.info(
            "Binding OSC server of %s process to socket %s"
            % (socket_name, socket_options)
        )
        if socket_options["family"] == "unix":
            socket_file = Path(socket_options["address"])
            if socket_file.exists():
                # We must delete dead socket file, else "Address already in use" error occurs when listening!
                # But BEWARE, if this socket was not really dead, this will create conflicts with existing listening processes!
                socket_file.unlink()
        server.listen(default=True, **socket_options)

    return server, starter_callback


def get_osc_client(to_app):

    socket_index = 0 if to_app else 1
    socket_options = _get_osc_socket_options(socket_index=socket_index)

    socket_family = socket_options.pop("family")
    sock = socket.socket(
        socket.AF_UNIX if socket_family == "unix" else socket.AF_INET, socket.SOCK_DGRAM
    )
    socket_options["sock"] = sock
    client = OSCClient(encoding="utf8", **socket_options)

    return client
