import logging
import sys
from datetime import time


class SafeUtcFormatter(logging.Formatter):

    """
    Custom formatter enforcing the use of GMT times in logging output, and blocks formatting errors
    """

    converter = time.gmtime  # Enforces UTC times in logs !

    def format(self, record):

        if record.args:

            # We merge arguments by ourselves, to manage potential formatting errors

            try:
                message = record.msg % record.args
            except Exception:
                try:
                    _message = repr(record.msg) + " -- " + repr(record.args)
                    message = _message.replace("%", "$") # make it safe regarding string interpolation
                except Exception:
                    # might happen if some magic stuffs in args can't be repr()ed
                    message = repr(record.msg) + "-- <NOREPR>"

                alert = "!!! CRITICAL ERROR IN CUSTOM LOGGING RECORD FORMATTING: %r" % message
                print(alert, file=sys.stderr)

            # we replace previous values
            record.msg = message
            record.args = tuple()

        return logging.Formatter.format(self, record)

