import threading
from pathlib import Path


ASSETS_PATH = Path(__file__).parents[1].joinpath("assets")


class InterruptableEvent(threading.Event):
    """An Event which handles ctrl-C on Windows too"""
    def wait(self, timeout=None):
        wait = super().wait  # get once, use often
        if timeout is None:
            while not wait(0.1):  pass
        else:
            wait(timeout)


def get_guilib_asset_path(*path_components):
    return str(ASSETS_PATH.joinpath(*path_components))
