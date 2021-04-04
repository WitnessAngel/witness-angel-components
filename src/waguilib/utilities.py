import threading


class InterruptableEvent(threading.Event):
    """An Event which handles ctrl-C on Windows too"""
    def wait(self, timeout=None):
        wait = super().wait  # get once, use often
        if timeout is None:
            while not wait(0.1):  pass
        else:
            wait(timeout)
