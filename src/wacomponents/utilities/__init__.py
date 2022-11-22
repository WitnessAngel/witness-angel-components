import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from textwrap import indent
from typing import Optional

from kivy.uix.filechooser import filesize_units

from wacomponents.i18n import tr

ASSETS_PATH = Path(__file__).parents[1].joinpath("assets")

COLON = lambda: tr._(": ")  # LAZY
LINEBREAK = "\n"
TEXT_INDENT = 4 * " "
SPACE = " "


MONOTHREAD_POOL_EXECUTOR = ThreadPoolExecutor(
    max_workers=1, thread_name_prefix="authenticator_keygen_worker"  # SINGLE worker for now, to avoid concurrency
)

class InterruptableEvent(threading.Event):
    """An Event which handles ctrl-C on Windows too"""

    def wait(self, timeout=None):
        wait = super().wait  # get once, use often
        if timeout is None:
            while not wait(0.1):  pass
        else:
            wait(timeout)


def get_system_information(disk_storage_path: Path):
    """Return a dict of information about connections, ram, and the partition of disk_storage_path.

    Handles unexisting folders too."""
    import psutil

    def _to_size_str(stat):
        if stat is None:
            return "?"
        return convert_bytes_to_human_representation(stat)

    def _to_percent_str(stat):
        if stat is None:
            return "?%"
        return "%s%%" % int(stat)

    virtual_memory = psutil.virtual_memory()
    available_memory = virtual_memory.available
    available_memory_percent = 100 * available_memory / virtual_memory.total

    try:
        _disk_usage = psutil.disk_usage(disk_storage_path)  # or shutil.disk_usage(path)?
        available_disk = _disk_usage.free
        available_disk_percent = 100 * available_disk / _disk_usage.total
    except FileNotFoundError:
        available_disk = None
        available_disk_percent = None

    net_if_stats = psutil.net_if_stats()  # Can return wrong eth0 status if psutil<=5.5.1
    wifi_status = False
    ethernet_status = False
    for key, value in net_if_stats.items():
        if value.isup:
            if key.startswith("eth"):
                ethernet_status = True
            elif key.startswith("wlan"):
                wifi_status = True
            # Ignore loopback etc.

    now_datetime = datetime.now()

    return {
        "disk_left": "%s  (%s)" % (_to_size_str(available_disk), _to_percent_str(available_disk_percent)),
        "ram_left": "%s  (%s)" % (_to_size_str(available_memory), _to_percent_str(available_memory_percent)),
        "wifi_status": "ON" if wifi_status else "OFF",
        "ethernet_status": "ON" if ethernet_status else "OFF",
        "now_datetime": now_datetime,
    }


def convert_bytes_to_human_representation(size):
    """Select the best representation for data size"""
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return "%i%s" % (int(size), x)
        size /= 1024.0
    return size


def shorten_uid(uid):
    return "..." + str(uid).split("-")[-1]


def get_nice_size(size):
    for unit in filesize_units:
        if size < 1024.0:
            return "%1.0f %s" % (size, unit)
        size /= 1024.0
    return size


# Utilities for formatted text

def indent_text(string, indent_value=TEXT_INDENT):
    string_indented = indent(string, indent_value)
    return string_indented

def format_keypair_label(key_algo: str, keychain_uid: uuid.UUID, private_key_present=None, error_on_missing_key=True,
                         short_uid=True) -> str:

    if short_uid:
        keychain_uid = shorten_uid(keychain_uid)

    keypair_label = "{key_algo} {keychain_uid}".format(
        key_algo=key_algo.replace("_", "-"),
        keychain_uid=keychain_uid)

    if private_key_present is not None:
        if private_key_present:
            if error_on_missing_key:
                label_suffix = ""  # Persence is expected, so nothing to display
            else:
                label_suffix = tr._("(private key present)")
        else:
            if error_on_missing_key:
                label_suffix = tr._("(missing private key)")
            else:
                label_suffix = tr._("(private key not present)")
        if label_suffix:
            keypair_label += " " + label_suffix

    return keypair_label


def format_authenticator_label(authenticator_owner: str, keystore_uid: uuid.UUID, trustee_type: Optional[str] = None,
                               short_uid=True):
    # Paul Duport (ID … 1abfb5411)"
    if short_uid:
        keystore_uid = shorten_uid(keystore_uid)
    authenticator_label = "{authenticator_owner} (ID {keystore_uid}".format(authenticator_owner=authenticator_owner,
                                                                            keystore_uid=keystore_uid)
    if trustee_type:
        authenticator_label += ", type {trustee_type}".format(trustee_type=trustee_type)

    authenticator_label += ")"
    return authenticator_label


def format_revelation_request_label(revelation_request_creation_datetime: datetime,
                                    revelation_request_uid: uuid.UUID,
                                    keystore_owner=None,
                                    short_uid=True):
    # Request ... 1abfb5411 (2022/05/22)

    if short_uid:
        revelation_request_uid = shorten_uid(revelation_request_uid)

    # Date into isoformat
    reformatted_revelation_request_creation_date = format_utc_datetime_label(
        field_datetime=revelation_request_creation_datetime, show_time=False)

    revelation_request_label = tr._("Request {revelation_request_uid} ({reformatted_revelation_request_creation_date})").format(
        revelation_request_uid=revelation_request_uid,
        reformatted_revelation_request_creation_date=reformatted_revelation_request_creation_date)

    if keystore_owner:
        revelation_request_label += tr._(" for {keystore_owner}").format(keystore_owner=keystore_owner)

    return revelation_request_label


def format_utc_datetime_label(field_datetime: datetime, show_time=False):
    # Displays "Created on: 2022-08-03"
    assert field_datetime.utcoffset().total_seconds() == 0, field_datetime.utcoffset()  # We want only UTC datetimes here

    # Extract et convert to string date
    datetime_label = field_datetime.date().isoformat()

    if show_time:
        field_time_str = field_datetime.time().replace(microsecond=0).isoformat()
        datetime_label += SPACE + tr._("at") + SPACE + field_time_str + " UTC"

    return datetime_label


def format_cryptainer_label(cryptainer_name: str, cryptainer_uid: Optional[uuid.UUID] = None,
                            cryptainer_size_bytes=None, short_uid=True):

    # (format de la MDList des cryptainers)
    # 20220109_202157_cryptainer.mp4.crypt (ID ... 1abfb5411) [6528 Ko]

    cryptainer_label = "{cryptainer_name}".format(cryptainer_name=cryptainer_name)

    if cryptainer_uid:
        if short_uid:
            cryptainer_uid = shorten_uid(cryptainer_uid)
        cryptainer_label += " (ID {cryptainer_uid})".format(cryptainer_uid=cryptainer_uid)

    if cryptainer_size_bytes is not None:
        cryptainer_label += " [{cryptainer_size_bytes}]".format(cryptainer_size_bytes=cryptainer_size_bytes)
    return cryptainer_label


def format_revelation_request_error(error_criticity: str, error_type: str, error_message: str, error_exception):
    # Criticity: ASYMMETRIC_DECRYPTION_ERROR
    # Message:
    # Exception:

    error_exception_suffix = ""
    if error_exception:
        error_exception_suffix = " (%s)" % error_exception.__class__.__name__

    error_label = error_criticity + COLON() + error_type.replace("_", " ").title() + error_exception_suffix + LINEBREAK +\
                  tr._("Message") + COLON() + error_message
    return error_label
