from pathlib import Path

import kivy.resources


def register_common_resources():

    # IF WE NEED ASSETS IN PROGRAM REPO ROOT
    # Returns path containing content - either locally or in pyinstaller tmp file'''
    #if hasattr(sys, '_MEIPASS'):
    #    return os.path.join(sys._MEIPASS)

    kivy.resources.resource_add_path(Path(__file__).parent)
