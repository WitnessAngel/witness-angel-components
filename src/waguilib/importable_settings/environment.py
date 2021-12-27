import os
from pathlib import Path

from kivy import platform

from plyer import storagepath


ACTIVITY_CLASS = "org.kivy.android.PythonActivity"
SERVICE_START_ARGUMENT = ""

IS_ANDROID = (platform == "android")

WACLIENT_TYPE = os.environ.get("WACLIENT_TYPE", "<UNKNOWN>")   # Typically "SERVICE" or "APPLICATION"


# Internal directories, specifically protected on mobile devices

if IS_ANDROID:
    from jnius import autoclass
    from android import mActivity

    if mActivity:
        # WE ARE IN MAIN APP (safer than WACLIENT_TYPE)
        CONTEXT = mActivity
    else:
        # WE ARE IN SERVICE!!!
        CONTEXT = autoclass("org.kivy.android.PythonService").mService

    INTERNAL_APP_ROOT = Path(CONTEXT.getFilesDir().toString())
    INTERNAL_CACHE_DIR = Path(CONTEXT.getCacheDir().toString())
    Environment = autoclass("android.os.Environment")
    EXTERNAL_APP_PREFIX = Environment.getExternalStorageDirectory().toString()  # Can be stripped as <sdcard>
    EXTERNAL_APP_ROOT = (
        Path(EXTERNAL_APP_PREFIX) / "WitnessAngel"
    )

    PackageManager = autoclass('android.content.pm.PackageManager')  # Precached for permission checking

else:
    CONTEXT = None  # Unused on Desktop
    _base_dir = Path(storagepath.get_home_dir()) / "WitnessAngel"
    INTERNAL_APP_ROOT = _base_dir
    INTERNAL_CACHE_DIR = INTERNAL_APP_ROOT / "Cache"  # FIXME move that to Internal ?? Why different from LOGS ?
    EXTERNAL_APP_PREFIX = None
    EXTERNAL_APP_ROOT = INTERNAL_APP_ROOT / "External"


    PackageManager = None

INTERNAL_APP_ROOT.mkdir(exist_ok=True, parents=True)  # Creates base directory too!
INTERNAL_CACHE_DIR.mkdir(exist_ok=True)


# Created/deleted by app, looked up by daemon service on boot/restart
WIP_RECORDING_MARKER = INTERNAL_APP_ROOT / "recording_in_progress"  

INTERNAL_LOGS_DIR = INTERNAL_APP_ROOT / "Logs"
INTERNAL_LOGS_DIR.mkdir(exist_ok=True)

INTERNAL_AUTHENTICATOR_DIR = INTERNAL_APP_ROOT / "Authenticator"
INTERNAL_AUTHENTICATOR_DIR.mkdir(exist_ok=True)

INTERNAL_KEYS_DIR = INTERNAL_APP_ROOT / "Keystore"
INTERNAL_KEYS_DIR.mkdir(exist_ok=True)

INTERNAL_CRYPTAINER_DIR = INTERNAL_APP_ROOT / "Containers"  # FIXME rename
INTERNAL_CRYPTAINER_DIR.mkdir(exist_ok=True)

EXTERNAL_DATA_EXPORTS_DIR = EXTERNAL_APP_ROOT / "DataExports"  # Might no exist yet (and require permissions!)


def strip_external_app_prefix(path):  # FIXME rename this, make it mor clear
    if not path:
        return ""
    path = str(path)  # Convert from Path if needed
    if EXTERNAL_APP_PREFIX and path.startswith(EXTERNAL_APP_PREFIX):
        path = path[len(EXTERNAL_APP_PREFIX):]
        path = "<sdcard>" + path  # e.g. sdcard/subfolder/...
    return path
