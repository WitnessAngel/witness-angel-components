import threading
from datetime import datetime
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


def get_system_information(disk_storage_path):
    """Return a dict of information about connections, ram, and the partition of disk_storage_path"""
    import psutil

    def _to_bytes_size_str(stat):
        return convert_bytes_to_human_representation(stat)
    def _to_percent_str(stat):
        return "%s%%" % int(stat)

    virtual_memory = psutil.virtual_memory()
    available_memory = virtual_memory.available
    available_memory_percent = 100 * available_memory / virtual_memory.total

    disk_usage = psutil.disk_usage(disk_storage_path)  # or shutil.disk_usage(path)?
    available_disk = disk_usage.free
    available_disk_percent = 100 * available_disk / disk_usage.total

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
        #"containers": "76",
    }


def convert_bytes_to_human_representation(size):
    """Select the best representation for data size"""
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return "%i%s" % (int(size), x)
        size /= 1024.0
    return size
