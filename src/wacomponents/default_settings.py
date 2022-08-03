"""
These settings should preferably be star-imported by setting files of actual projects, not directly referenced.
"""
from pathlib import Path

import os
from kivy import platform
from plyer import storagepath

ACTIVITY_CLASS = "org.kivy.android.PythonActivity"
SERVICE_START_ARGUMENT = ""

IS_ANDROID = (platform == "android")
IS_IOS = (platform == "ios")
IS_MOBILE = IS_ANDROID or IS_IOS


def _strip_filepath_scheme(filepath):
    # MacOSX returns file:// URLs (do not use str.removeprefix() else python retrocompatibility issues)
    if filepath.startswith("file://"):
        filepath = filepath[len("file://"):]
        assert filepath.startswith("/")
    return filepath


# Internal directories, specifically protected on mobile devices

if IS_ANDROID:
    from jnius import autoclass
    from android import mActivity

    if mActivity:
        # WE ARE IN MAIN APP
        ANDROID_CONTEXT = mActivity
    else:
        # WE ARE IN SERVICE!!!
        ANDROID_CONTEXT = autoclass("org.kivy.android.PythonService").mService

    INTERNAL_APP_ROOT = Path(ANDROID_CONTEXT.getFilesDir().toString())
    INTERNAL_CACHE_DIR = Path(ANDROID_CONTEXT.getCacheDir().toString())
    Environment = autoclass("android.os.Environment")
    EXTERNAL_APP_ROOT_PREFIX = Environment.getExternalStorageDirectory().toString()  # Can be stripped as <sdcard>
    EXTERNAL_APP_ROOT = (
        Path(EXTERNAL_APP_ROOT_PREFIX) / "WitnessAngel"
    )

    AndroidPackageManager = autoclass('android.content.pm.PackageManager')  # Precached for permission checking

elif IS_IOS:
    # iOS apps are SANDBOXED, no common "external folder" to write to
    from plyer import storagepath
    _home_dir = Path(_strip_filepath_scheme(storagepath.get_home_dir()))

    INTERNAL_APP_ROOT = _home_dir / "Library" / "Application Support"  # Might NOT EXIST yet
    INTERNAL_CACHE_DIR = _home_dir / "tmp"
    EXTERNAL_APP_ROOT_PREFIX = None
    EXTERNAL_APP_ROOT = _home_dir / "Documents"  # Will be accessible to Files thanks to special xcode flags

else:
    _home_dir = _strip_filepath_scheme(storagepath.get_home_dir())
    INTERNAL_APP_ROOT = Path(_home_dir) / ".witnessangel"
    INTERNAL_CACHE_DIR = INTERNAL_APP_ROOT / "cache"
    EXTERNAL_APP_ROOT_PREFIX = None
    EXTERNAL_APP_ROOT = INTERNAL_APP_ROOT / "external"

print(">> DETECTED INTERNAL_APP_ROOT is ", INTERNAL_APP_ROOT)
INTERNAL_APP_ROOT.mkdir(exist_ok=True, parents=True)  # Creates base directory too!
INTERNAL_CACHE_DIR.mkdir(exist_ok=True)


# Created/deleted by app, looked up by daemon service on boot/restart
WIP_RECORDING_MARKER = INTERNAL_APP_ROOT / "recording_in_progress"

INTERNAL_LOGS_DIR = INTERNAL_APP_ROOT / "logs"
INTERNAL_LOGS_DIR.mkdir(exist_ok=True)

INTERNAL_AUTHENTICATOR_DIR = INTERNAL_APP_ROOT / "authenticator.keystore"
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
