from waguilib.android_helpers import patch_ctypes_module
from waguilib.importable_settings import IS_ANDROID


def setup_generic_app(package):
    """Setup for both gui and console apps."""
    import os
    if os.getenv("WACLIENT_ENABLE_TYPEGUARD"):
        from typeguard.importhook import install_import_hook
        install_import_hook(package)

    if IS_ANDROID:
        patch_ctypes_module()  # Necessary for wacryptolib
