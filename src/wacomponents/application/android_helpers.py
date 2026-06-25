# This file is part of Witness Angel Components
# SPDX-FileCopyrightText: Copyright Prolifik SARL
# SPDX-License-Identifier: GPL-2.0-or-later

import os

PACKAGE_NAME = os.getenv("WA_PACKAGE_NAME")  # Java package name here  FIXME BROKEN
CHANNEL_ID = PACKAGE_NAME


def preload_java_classes():
    """
    Workaround so that pyjnius/JNI finds java classes even from secondary thread.

    Function to be called from main process thread!
    """
    from jnius import autoclass

    autoclass("org.jnius.NativeInvocationHandler")
    autoclass("android.graphics.BitmapFactory")
    autoclass("{}.R$drawable".format(PACKAGE_NAME))
    autoclass("android.content.Intent")
    autoclass("android.app.PendingIntent")
    autoclass("android.app.NotificationManager")
    autoclass("android.app.NotificationChannel")
    autoclass("android.app.Notification$Builder")
    autoclass("android.content.Context")
    autoclass("java.lang.String")


def _set_icons(context, notification, icon=None):
    """
    Set the small application icon displayed at the top panel together with
    WiFi, battery percentage and time and the big optional icon (preferably
    PNG format with transparent parts) displayed directly in the
    notification body.
    .. versionadded:: 1.4.0
    """

    from jnius import autoclass

    BitmapFactory = autoclass("android.graphics.BitmapFactory")
    Drawable = autoclass("{}.R$drawable".format(PACKAGE_NAME))

    app_icon = Drawable.icon
    notification.setSmallIcon(app_icon)

    """
    if icon == '':
            # we don't want the big icon set,
            # only the small one in the top panel
            pass
    elif icon:
        bitmap_icon = BitmapFactory.decodeFile(icon)
        notification.setLargeIcon(bitmap_icon)
    else:
        bitmap_icon = BitmapFactory.decodeResource(
            python_act.getResources(), app_icon
        )
        notification.setLargeIcon(bitmap_icon)
    """


def _set_open_behavior(context, notification):
    """
    Open the source application when user opens the notification.
    .. versionadded:: 1.4.0
    """

    from jnius import autoclass

    Intent = autoclass("android.content.Intent")
    PendingIntent = autoclass("android.app.PendingIntent")
    from android import python_act

    # create Intent that navigates back to the application
    app_context = context.getApplication().getApplicationContext()
    notification_intent = Intent(app_context, python_act)

    # set flags to run our application Activity
    notification_intent.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
    notification_intent.setAction(Intent.ACTION_MAIN)
    notification_intent.addCategory(Intent.CATEGORY_LAUNCHER)

    # get our application Activity
    pending_intent = PendingIntent.getActivity(app_context, 0, notification_intent, 0)

    notification.setContentIntent(pending_intent)
    notification.setAutoCancel(False)


def build_notification_channel(context, name):
    from jnius import autoclass

    manager = autoclass("android.app.NotificationManager")  # -> "notification"
    channel = autoclass("android.app.NotificationChannel")

    app_channel = channel(CHANNEL_ID, name, manager.IMPORTANCE_DEFAULT)
    context.getSystemService("notification").createNotificationChannel(app_channel)
    return app_channel


def build_notification(context, title, message, ticker):
    from jnius import autoclass

    AndroidString = autoclass("java.lang.String")

    NotificationBuilder = autoclass("android.app.Notification$Builder")

    notification = NotificationBuilder(context, CHANNEL_ID)

    # set basic properties for notification
    notification.setContentTitle(title)
    notification.setContentText(AndroidString(message))
    notification.setTicker(AndroidString(ticker))

    # set additional flags for notification
    _set_icons(context, notification, icon=None)
    _set_open_behavior(context, notification)

    notification = notification.build()
    return notification


def display_notification(context, notification):
    from jnius import autoclass

    Context = autoclass("android.content.Context")

    notification_service = context.getSystemService(Context.NOTIFICATION_SERVICE)
    notification_service.notify(0, notification)


def patch_ctypes_module_for_android():
    """ctypes.pythonapi fails on Android due to wrong ctypes.PyDLL(None) setup"""
    import ctypes, sys

    ctypes.pythonapi = ctypes.PyDLL("libpython%d.%d.so" % sys.version_info[:2])


def monitor_android_safe_area_insets(on_insets_changed):
    """
    Watch Android system-bar (status + navigation bar) insets and report them as
    [left, top, right, bottom] *pixels* via ``on_insets_changed`` (called on the Kivy thread).

    Correct on any Android version: on non-edge-to-edge windows the content view receives
    already-consumed insets (zeros) -> no double margin; on edge-to-edge windows
    (Android 15 / SDK 35+ enforced) it receives the real insets. Re-fires on rotation,
    nav-mode change, keyboard and multi-window.

    Returns the listener; the caller MUST keep a reference to it, otherwise the
    Python/Java proxy gets garbage-collected and stops firing.
    """
    from jnius import autoclass, PythonJavaClass, java_method
    from android.runnable import run_on_ui_thread
    from kivy.clock import Clock

    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    VERSION = autoclass("android.os.Build$VERSION")

    def _extract(insets):
        if insets is None:
            return [0, 0, 0, 0]
        if VERSION.SDK_INT >= 30:  # Android 11+ : typed insets API
            Type = autoclass("android.view.WindowInsets$Type")
            i = insets.getInsets(Type.systemBars())
            return [i.left, i.top, i.right, i.bottom]
        return [  # API 23-29 (minapi is 26 here)
            insets.getSystemWindowInsetLeft(),
            insets.getSystemWindowInsetTop(),
            insets.getSystemWindowInsetRight(),
            insets.getSystemWindowInsetBottom(),
        ]

    class _InsetsListener(PythonJavaClass):
        __javainterfaces__ = ["android/view/View$OnApplyWindowInsetsListener"]
        __javacontext__ = "app"

        @java_method("(Landroid/view/View;Landroid/view/WindowInsets;)Landroid/view/WindowInsets;")
        def onApplyWindowInsets(self, view, insets):
            margins = _extract(insets)
            Clock.schedule_once(lambda dt: on_insets_changed(margins), 0)
            return insets  # Do not consume, let descendant views receive them too

    listener = _InsetsListener()

    @run_on_ui_thread
    def _install():
        activity = PythonActivity.mActivity
        content = activity.findViewById(autoclass("android.R$id").content)
        content.setOnApplyWindowInsetsListener(listener)
        content.requestApplyInsets()  # Force an immediate first dispatch

    _install()
    return listener
