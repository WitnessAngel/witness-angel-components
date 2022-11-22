import logging


def _presetup_app_environment(setup_kivy_gui: bool):
    """Setup for both gui and console apps.

    this module uses print() instead of logging because the state of app is not clear at this moment.
    """
    import os

    os.environ["KIVY_NO_ARGS"] = "1"  # Important to bypass Kivy CLI system

    try:

        protected_app_package = os.getenv("ENABLE_TYPEGUARD")
        if protected_app_package:
            from typeguard.importhook import install_import_hook
            install_import_hook(protected_app_package)

    except Exception as exc:
        print(">>>>>>>> FAILED INITIALIZATION OF TYPEGUARD: %r" % exc)

    try:

        from wacomponents.default_settings import IS_ANDROID, IS_MOBILE
        from wacomponents.application.android_helpers import patch_ctypes_module_for_android
        if IS_ANDROID:
            patch_ctypes_module_for_android()  # Necessary for wacryptolib

            from jnius import autoclass
            from android.runnable import Runnable

            def config_real():
                python_activity_class = autoclass("org.kivy.android.PythonActivity")
                python_activity_instance = python_activity_class.mActivity
                android_window = python_activity_instance.getWindow()
                android_window.addFlags(2)  # Constant LAYOUT_IN_DISPLAY_CUTOUT_MODE_NEVER
                #print(">>>>>>>> Called android_window.addFlags(LAYOUT_IN_DISPLAY_CUTOUT_MODE_NEVER) !")
            Runnable(config_real)()

    except Exception as exc:
        print(">>>>>>>> FAILED ANDROID PRESETUP: %r" % exc)

    try:

        # Add paths to image/font/sound assets, for e-paper too!
        from wacomponents.assets import register_common_resources
        register_common_resources()

    except Exception as exc:
        print(">>>>>>>> FAILED REGISTRATION OF COMMON RESOURCES: %r" % exc)

    try:

        # WORKAROUND FOR LOGGING AND GRAPHICS WEIRDNESS IN KIVY SETUP #

        import sys
        custom_kivy_stream_handler = logging.StreamHandler()
        sys._kivy_logging_handler = custom_kivy_stream_handler
        from kivy.logger import Logger as logger  # Trigger init of Kivy logging
        del logger

        # Finish ugly monkey-patching by Kivy
        assert logging.getLogger("kivy") is logging.root
        logging.Logger.root = logging.root
        logging.Logger.manager.root = logging.root

    except Exception as exc:
        print(">>>>>>>> FAILED REPAIR OF KIVY LOGGING: %r" % exc)

    # COMMON LOGGING TWEAKS
    logging_level_str = os.getenv("LOGGING_LEVEL", default="INFO").upper()
    logging.root.setLevel(getattr(logging, logging_level_str))
    logging.disable(0)
    logging.info("Default logging level set to %s, use LOGGING_LEVEL environment variable to change it", logging_level_str)
    #import logging_tree ; logging_tree.printout()  # To display the actual logging setup

    if not setup_kivy_gui:
        return  # Cancel the rest of setups

    try:

        # SETUP THE APP WINDOW AND ITS HELPERS

        from wacomponents.default_settings import IS_MOBILE

        from kivy.config import Config
        ''' # In case:
        Config.set('graphics', 'top', '50')
        Config.set('graphics', 'left', '50')
        Config.set('graphics', 'position', 'custom')
        Config.set("graphics", "fullscreen", "0")
        Config.set("graphics", "show_cursor", "1")
        '''

        from kivy.core.window import Window
        ##Window.minimum_width, Window.minimum_height = Window.size = (600, 600)

        if not IS_MOBILE:
            # Disable multitouch emulation red dots on Desktop, on right/middle clicks
            Config.set('input', 'mouse', 'mouse,disable_multitouch,disable_on_activity')

        # HACK TO TEMPORARILY EMULATE TOUCHSCREEN ON DESKTOP WHEN NEEDED:
        #Config.set('kivy', 'desktop', 0)

        # HACK to ensure that we don't need to click TWICE to gain focus on Kivy Window and then on widget:
        # https://stackoverflow.com/questions/53337630/kivy-on-windows10-how-to-click-a-button-when-kivy-application-does-not-in-focu
        def force_window_focus(*args, **kwargs):
            Window.raise_window()
        Window.bind(on_cursor_enter=force_window_focus)

        from wacomponents.widgets.layout_components import load_layout_helper_widgets
        load_layout_helper_widgets()  # Widgets useful a bit everywhere

    except Exception as exc:
        print(">>>>>>>> FAILED INITIALIZATION OF KIVY WINDOW AND ASSETS: %r" % exc)
        raise

