
# WORKAROUND FOR LOGGING WEIRDNESS IN KIVY SETUP #
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
    logging.root.setLevel(logging.DEBUG)
    logging.disable(0)

    # import logging_tree
    # logging_tree.printout()

    #if sys.platform == "win32":
    #    os.environ["KIVY_GL_BACKEND"] = "angle_sdl2"

except Exception as exc:
    print(">>>>>>>> FAILED INITIALIZATION OF WA GUI LOGGING: %r" % exc)


# SETUP INITIAL STATE OF THE WINDOW
try:
    from kivy.config import Config
    Config.set('graphics', 'top', '50')
    Config.set('graphics', 'left', '50')
    Config.set('graphics', 'position', 'custom')
    # FIXME this happens too late I guess
    #Config.set("graphics", "fullscreen", "0")
    #Config.set("graphics", "show_cursor", "1")

    from kivy.core.window import Window
    Window.minimum_width, Window.minimum_height = Window.size = (500, 380)
except Exception as exc:
    print(">>>>>>>> FAILED INITIALIZATION OF WA GUI WINDOW: %r" % exc)
