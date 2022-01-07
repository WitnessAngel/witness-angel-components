from typing import List
import time

from wacomponents.default_settings import IS_ANDROID, CONTEXT, PackageManager, EXTERNAL_EXPORTS_DIR


def request_multiple_permissions(permissions: List[str]) -> List[bool]:
    """Returns nothing."""
    if IS_ANDROID:
        from android.permissions import request_permissions, Permission
        permissions_qualified_names = [
            getattr(Permission, permission) for permission in permissions
        ]
        request_permissions(
                permissions_qualified_names
        )  # Might freeze app while showing user a popup


def request_single_permission(permission: str) -> bool:
    """Returns nothing."""
    request_multiple_permissions([permission])


def has_single_permission(permission: str) -> bool:
    """Returns True iff permission was granted."""
    #from kivy.logger import Logger as logger  # Delayed import
    if IS_ANDROID:
        # THIS ONLY WORKS FOR ACTIVITIES: "from android.permissions import check_permission, Permission"
        from android.permissions import Permission
        permission_qualified_name = getattr(Permission, permission)  # e.g. android.permission.ACCESS_FINE_LOCATION
        res = CONTEXT.checkSelfPermission(permission_qualified_name)
        #logger.info("checkSelfPermission returned %r (vs %s) for %s" % (res, PackageManager.PERMISSION_GRANTED, permission))
        return (res == PackageManager.PERMISSION_GRANTED)
    return True  # For desktop OS


def warn_if_permission_missing(permission: str) -> bool:
    """Returns True iff a warning was emitted and permission is missing."""
    from kivy.logger import Logger as logger  # Delayed import
    if IS_ANDROID:
        if not has_single_permission(permission=permission):
            logger.warning("Missing permission %s, cancelling use of corresponding sensor" % permission)
            return True
    return False


def request_external_storage_dirs_access():  # FIXME rename to request_external_storage_dir_access()?
    """Ask for write permission and create missing directories."""
    if IS_ANDROID:
        from kivy.logger import Logger as logger  # Delayed import
        permission = "WRITE_EXTERNAL_STORAGE"
        request_single_permission(permission)
        # FIXME remove this ugly sleep() hack and move this to Service
        time.sleep(3)  # Let the callback permission request be processed
        res = has_single_permission(permission)
        #logger.info("Has single permission %r is %s" % (permission, res))
        if not res:
            return False
    EXTERNAL_EXPORTS_DIR.mkdir(parents=True, exist_ok=True)  # On ALL environments!
    return True
