

def _presetup_app_environment(setup_kivy):
    """Setup for both gui and console apps."""
    import os

    try:

        protected_app_package = os.getenv("ENABLE_TYPEGUARD")
        if protected_app_package:
            from typeguard.importhook import install_import_hook
            install_import_hook(protected_app_package)

    except Exception as exc:
        print(">>>>>>>> FAILED INITIALIZATION OF TYPEGUARD: %r" % exc)

    try:
        from waguilib.importable_settings import IS_ANDROID
        from waguilib.application.android_helpers import patch_ctypes_module_for_android
        if IS_ANDROID:
            patch_ctypes_module_for_android()  # Necessary for wacryptolib

    except Exception as exc:
        print(">>>>>>>> FAILED CTYPES PATCHING ON ANDROID: %r" % exc)

    if not setup_kivy:
        return  # Cancel the rest of setups

    try:

        # WORKAROUND FOR LOGGING AND GRAPHICS WEIRDNESS IN KIVY SETUP #

        import logging
        import sys
        custom_kivy_stream_handler = logging.StreamHandler()
        sys._kivy_logging_handler = custom_kivy_stream_handler
        from kivy.logger import Logger as logger  # Trigger init of Kivy logging
        del logger

        # Finish ugly monkey-patching by Kivy
        assert logging.getLogger("kivy") is logging.root
        logging.Logger.root = logging.root
        logging.Logger.manager.root = logging.root

        # For now allow EVERYTHING
        logging.root.setLevel(logging.INFO)
        logging.disable(0)

        # import logging_tree
        # logging_tree.printout()

    except Exception as exc:
        print(">>>>>>>> FAILED INITIALIZATION OF KIVY LOGGING: %r" % exc)

    try:

        # SETUP THE APP WINDOW AND ITS ASSETS/HELPERS

        # Add paths to image/font/sound assets
        from waguilib.assets import register_common_resources
        register_common_resources()

        from waguilib.importable_settings import WACLIENT_TYPE, IS_ANDROID

        if WACLIENT_TYPE == "APPLICATION":
            from kivy.config import Config
            '''
            Config.set('graphics', 'top', '50')
            Config.set('graphics', 'left', '50')
            Config.set('graphics', 'position', 'custom')
            '''
            # FIXME this happens too late it seems
            #Config.set("graphics", "fullscreen", "0")
            #Config.set("graphics", "show_cursor", "1")

            from kivy.core.window import Window
            ##Window.minimum_width, Window.minimum_height = Window.size = (600, 600)

            if not IS_ANDROID:
                # Disable multitouch emulation red dots on Desktop, on right/middle clicks
                Config.set('input', 'mouse', 'mouse,disable_multitouch')

            # Ensure that we don't need to click TWICE to gain focus on Kivy Window and then on widget!
            def force_window_focus(*args, **kwargs):
                Window.raise_window()
            Window.bind(on_cursor_enter=force_window_focus)

            from waguilib.widgets.layout_components import load_layout_helper_widgets
            load_layout_helper_widgets()

    except Exception as exc:
        print(">>>>>>>> FAILED INITIALIZATION OF KIVY WINDOW AND ASSETS: %r" % exc)
        raise

