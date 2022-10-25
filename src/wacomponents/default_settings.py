"""
These settings should preferably be star-imported by setting files of actual projects, not directly referenced.
"""
from pathlib import Path

import os
from kivy import platform
from plyer import storagepath

ANDROID_ACTIVITY_CLASS = "org.kivy.android.PythonActivity"
SERVICE_START_ARGUMENT = ""

IS_ANDROID = (platform == "android")
IS_IOS = (platform == "ios")
IS_MOBILE = IS_ANDROID or IS_IOS


# Adapted from https://gist.github.com/barseghyanartur/94dbda2ad6f8937d6c307811ad51469a
def _is_raspberry_pi(raise_on_errors=False):
    """Checks if we're on a Raspberry PI.

    Returns a boolean or raises depending on raise_on_errors parameter."""
    from kivy import platform
    if platform != "linux":
        return False
    try:
        with open('/proc/cpuinfo', 'r') as cpuinfo:
            found = False
            for line in cpuinfo:
                if line.startswith('Hardware'):
                    found = True
                    label, value = line.strip().split(':', 1)
                    value = value.strip()
                    if value not in (
                        'BCM2708',
                        'BCM2709',
                        'BCM2835',
                        'BCM2836'
                    ):
                        if raise_on_errors:
                            raise ValueError(
                                'This system does not appear to be a '
                                'Raspberry Pi.'
                            )
                        else:
                            return False
            if not found:
                if raise_on_errors:
                    raise ValueError(
                        'Unable to determine if this system is a Raspberry Pi.'
                    )
                else:
                    return False
    except IOError:
        if raise_on_errors:
            raise ValueError('Unable to open `/proc/cpuinfo`.')
        else:
            return False

    return True

IS_RASPBERRY_PI = _is_raspberry_pi()
##print(">>>>>>> IS_RASPBERRY_PI value is", IS_RASPBERRY_PI)


# Everything is slow on a raspberry pi, so we take our time
WAIT_TIME_MULTIPLIER = 4 if IS_RASPBERRY_PI else 1


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
    # FIXME we must use getExternalFilesDir now!!
    EXTERNAL_APP_ROOT_PREFIX = Environment.getExternalStorageDirectory().toString()  # Can be stripped as <sdcard>
    _documents_folder = Path(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOCUMENTS).toString())
    EXTERNAL_APP_ROOT = _documents_folder.joinpath("WitnessAngel")

    AndroidPackageManager = autoclass('android.content.pm.PackageManager')  # Precached for permission checking

elif IS_IOS:
    # iOS apps are SANDBOXED, no common "external folder" to write to
    from plyer import storagepath
    _home_dir = Path(_strip_filepath_scheme(storagepath.get_home_dir()))

    INTERNAL_APP_ROOT = _home_dir / "Library" / "Application Support"  # Might NOT EXIST yet
    INTERNAL_CACHE_DIR = _home_dir / "tmp"
    EXTERNAL_APP_ROOT_PREFIX = None
    EXTERNAL_APP_ROOT = _home_dir / "Documents"  # Will be accessible to "Files" app, thanks to special xcode flags

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
if INTERNAL_AUTHENTICATOR_DIR.exists():
    pass
else:
    ANCIENT_INTERNAL_AUTHENTICATOR_DIR = INTERNAL_APP_ROOT / "authenticator"
    if ANCIENT_INTERNAL_AUTHENTICATOR_DIR.exists():
        ANCIENT_INTERNAL_AUTHENTICATOR_DIR.rename(INTERNAL_AUTHENTICATOR_DIR)

INTERNAL_KEYSTORE_POOL_DIR = INTERNAL_APP_ROOT / "keystore_pool"
INTERNAL_KEYSTORE_POOL_DIR.mkdir(exist_ok=True)

INTERNAL_CRYPTAINER_DIR = INTERNAL_APP_ROOT / "cryptainers"  # FIXME rename
INTERNAL_CRYPTAINER_DIR.mkdir(exist_ok=True)

EXTERNAL_EXPORTS_DIR = EXTERNAL_APP_ROOT / "exports"  # Might no exist yet (and require permissions!)

