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
    _EXTERNAL_APP_ROOT = (
        Path(Environment.getExternalStorageDirectory().toString()) / "WitnessAngel"
    )

    PackageManager = autoclass('android.content.pm.PackageManager')  # Precached for permission checking

else:
    CONTEXT = None  # Unused on Desktop
    INTERNAL_APP_ROOT = Path(storagepath.get_home_dir()) / "WitnessAngelInternal"
    _EXTERNAL_APP_ROOT = Path(storagepath.get_home_dir()) / "WitnessAngelExternal"
    INTERNAL_CACHE_DIR = Path(storagepath.get_home_dir()) / "WitnessAngelCache"

    PackageManager = None

INTERNAL_APP_ROOT.mkdir(exist_ok=True)
INTERNAL_CACHE_DIR.mkdir(exist_ok=True)


# Created/deleted by app, looked up by daemon service on boot/restart
WIP_RECORDING_MARKER = INTERNAL_APP_ROOT / "recording_in_progress"  

INTERNAL_LOGS_DIR = INTERNAL_APP_ROOT / "Logs"
INTERNAL_LOGS_DIR.mkdir(exist_ok=True)

INTERNAL_KEYS_DIR = INTERNAL_APP_ROOT / "KeyStorage"
INTERNAL_KEYS_DIR.mkdir(exist_ok=True)

INTERNAL_CONTAINERS_DIR = INTERNAL_APP_ROOT / "Containers"
INTERNAL_CONTAINERS_DIR.mkdir(exist_ok=True)

EXTERNAL_DATA_EXPORTS_DIR = _EXTERNAL_APP_ROOT / "DataExports"  # Might no exist yet (and require permissions!)

