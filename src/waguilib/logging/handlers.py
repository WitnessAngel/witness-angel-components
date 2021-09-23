import sys
from logging import Handler
from decorator import decorator
from kivy.logger import Logger as logger


class CallbackHandler(Handler):
    def __init__(self, gui_console_callback):
        super().__init__()
        self._gui_console_callback = gui_console_callback

    def emit(self, record):
        try:
            msg = self.format(record)
            self._gui_console_callback(msg)
        except Exception as exc:
            print(
                "Warning: exception in CallbackHandler when emitting record",
                record,
                "->",
                exc,
            )
            #import traceback
            #traceback.print_exc(file=sys.stdout)


@decorator
def safe_catch_unhandled_exception(f, *args, **kwargs):
    try:
        return f(*args, **kwargs)
    except Exception as exc:
        try:
            logger.error(
                f"Caught unhandled exception in call of function {f!r}: {exc!r}",
                exc_info=True
            )
            #import traceback
            #traceback.print_exc(file=sys.stdout)  # Important, since stderr is hooked by Kivy!
        except Exception as exc2:
            print(
                "Beware, service callback {f!r} and logging system are both broken: {exc2!r}"
            )
