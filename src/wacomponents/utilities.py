import threading
import uuid
from datetime import datetime, date
from pathlib import Path
from typing import Optional
from textwrap import indent

from kivy.uix.filechooser import filesize_units

from wacomponents.i18n import tr

ASSETS_PATH = Path(__file__).parents[1].joinpath("assets")

COLON = tr._(": ")
LINEBREAK = "\n"
INDENT_TEXT = 6 * " "

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

    def _to_bytes_size_str(stat):  # FIXME find better name
        return convert_bytes_to_human_representation(stat)

    def _to_percent_str(stat):
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
        "disk_left": "%s  (%s)" % (_to_bytes_size_str(available_disk), _to_percent_str(available_disk_percent)),
        "ram_left": "%s  (%s)" % (_to_bytes_size_str(available_memory), _to_percent_str(available_memory_percent)),
        "wifi_status": "ON" if wifi_status else "OFF",
        "ethernet_status": "ON" if ethernet_status else "OFF",
        "now_datetime": now_datetime,
        # "containers": "76",
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

def indent_text(string, indent_value = INDENT_TEXT):
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


def format_revelation_request_label(revelation_request_creation_datetime: datetime, revelation_request_uid: uuid.UUID,
                                    revelation_request_status: Optional[str] = None, short_uid=True):
    # Revelation request id: ... 1abfb5411 (Created on: 2022/05/22)

    if short_uid:
        revelation_request_uid = shorten_uid(revelation_request_uid)

    # Date into isoformat
    refformatted_revelation_request_creation_date = format_datetime_label(
        field_datetime=revelation_request_creation_datetime)

    revelation_request_label = "Revelation request (ID {revelation_request_uid}, created on: {refformatted_revelation_request_creation_date})".format(
        revelation_request_uid=revelation_request_uid,
        refformatted_revelation_request_creation_date=refformatted_revelation_request_creation_date)

    if revelation_request_status:
        revelation_request_label += ", Status: {revelation_request_status}".format(revelation_request_status=revelation_request_status)

    return revelation_request_label


def format_datetime_label(field_datetime: datetime, show_time=False):
    # Created on: 2022-08-03

    # Remove mcrosecond
    field_datetime = field_datetime.replace(microsecond=0)

    # Extract et convert to string date
    field_date_string = str(field_datetime.date())

    # Convert into isofromat(Japanese)
    refformatted_field_date = date.fromisoformat(field_date_string)

    datetime_label = "{refformatted_field_date}".format(refformatted_field_date=refformatted_field_date)

    if show_time:
        field_time_str = str(field_datetime.time())
        datetime_label += " at {field_time_str}".format(field_time_str=field_time_str)

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
    # Exception: ASYMMETRIC_DECRYPTION_ERROR
    if error_exception:
        error_exception = error_exception.__class__.__name__

    error_label = "{error_criticity}: {error_type}\n" \
                  "Message: {error_message}\n" \
                  "Exception: {error_exception}".format(error_criticity=error_criticity, error_type=error_type,
                                                        error_message=error_message, error_exception=error_exception)
    return error_label
