
# WORKAROUND FOR LOGGING AND GRAPHICS WEIRDNESS IN KIVY SETUP #

try:
    # MUST BE ROBUST DUE TO NEED FOR RESILIENT "CRASH HANDLER" ACCESS #

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

    #if sys.platform == "win32":
    #    os.environ["KIVY_GL_BACKEND"] = "angle_sdl2"

except Exception as exc:
    print(">>>>>>>> FAILED INITIALIZATION OF WA GUI LOGGING: %r" % exc)


# SETUP INITIAL STATE OF THE WINDOW
try:

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
        # FIXME this happens too late I guess
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

        from waguilib.widgets.layout_helpers import load_layout_helper_widgets
        load_layout_helper_widgets()

except Exception as exc:
    print(">>>>>>>> FAILED INITIALIZATION OF WA GUI WINDOW: %r" % exc)
    raise

