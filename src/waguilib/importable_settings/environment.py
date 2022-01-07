import os
from pathlib import Path

from kivy import platform

from plyer import storagepath


ACTIVITY_CLASS = "org.kivy.android.PythonActivity"
SERVICE_START_ARGUMENT = ""

IS_ANDROID = (platform == "android")

# FIXME REMOVE/CHANGE THIS WHOLE WACLIENT_TYPE thing?? setup_app_environment() should take care of that
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
    EXTERNAL_APP_ROOT_PREFIX = Environment.getExternalStorageDirectory().toString()  # Can be stripped as <sdcard>
    EXTERNAL_APP_ROOT = (
        Path(EXTERNAL_APP_ROOT_PREFIX) / "WitnessAngel"
    )

    PackageManager = autoclass('android.content.pm.PackageManager')  # Precached for permission checking

else:
    CONTEXT = None  # Unused on Desktop
    INTERNAL_APP_ROOT = Path(storagepath.get_home_dir()) / ".witnessangel"
    INTERNAL_CACHE_DIR = INTERNAL_APP_ROOT / "cache"
    EXTERNAL_APP_ROOT_PREFIX = None
    EXTERNAL_APP_ROOT = INTERNAL_APP_ROOT / "external"

    PackageManager = None

INTERNAL_APP_ROOT.mkdir(exist_ok=True, parents=True)  # Creates base directory too!
INTERNAL_CACHE_DIR.mkdir(exist_ok=True)


# Created/deleted by app, looked up by daemon service on boot/restart
WIP_RECORDING_MARKER = INTERNAL_APP_ROOT / "recording_in_progress"  

INTERNAL_LOGS_DIR = INTERNAL_APP_ROOT / "logs"
INTERNAL_LOGS_DIR.mkdir(exist_ok=True)

INTERNAL_AUTHENTICATOR_DIR = INTERNAL_APP_ROOT / "authenticator"
INTERNAL_AUTHENTICATOR_DIR.mkdir(exist_ok=True)

INTERNAL_KEYSTORE_POOL_DIR = INTERNAL_APP_ROOT / "keystore_pool"
INTERNAL_KEYSTORE_POOL_DIR.mkdir(exist_ok=True)

INTERNAL_CRYPTAINER_DIR = INTERNAL_APP_ROOT / "cryptainers"  # FIXME rename
INTERNAL_CRYPTAINER_DIR.mkdir(exist_ok=True)

EXTERNAL_EXPORTS_DIR = EXTERNAL_APP_ROOT / "exports"  # Might no exist yet (and require permissions!)


def strip_external_app_root_prefix(path):  # FIXME rename this, make it mor clear
    if not path:
        return ""
    path = str(path)  # Convert from Path if needed
    if EXTERNAL_APP_ROOT_PREFIX and path.startswith(EXTERNAL_APP_ROOT_PREFIX):
        path = path[len(EXTERNAL_APP_ROOT_PREFIX):]
        path = "<sdcard>" + path  # e.g. sdcard/subfolder/...
    return path
