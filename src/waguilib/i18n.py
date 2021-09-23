# -*- coding: utf-8 -*-

import gettext
import locale

import kivy
from kivy.lang import Observable


# VERY rough detection of user language, will often not work under Windows but it's OK
# See https://stackoverflow.com/a/25691701 and win32.GetUserDefaultUILanguage()
_lang_code, _charset = locale.getlocale()
DEFAULT_LANGUAGE = "fr" if "fr" in _lang_code.lower() else "en"


class Lang(Observable):
    """Internationalization of the program : https://github.com/tito/kivy-gettext-example"""

    observers = []
    lang = None

    def __init__(self, defaultlang, locale_dir):
        super(Lang, self).__init__()
        self.ugettext = None
        self.locale_dir = locale_dir
        self.switch_lang(defaultlang)


    def _(self, text):
        return self.ugettext(text)

    def fbind(self, name, func, args, **kwargs):
        if name == "_":
            self.observers.append((func, args, kwargs))
        else:
            return super(Lang, self).fbind(name, func, *args, **kwargs)

    def funbind(self, name, func, args, **kwargs):
        if name == "_":
            key = (func, args, kwargs)
            if key in self.observers:
                self.observers.remove(key)
        else:
            return super(Lang, self).funbind(name, func, *args, **kwargs)

    def switch_lang(self, lang):
        # instanciate a gettext
        locales = gettext.translation(
            "witnessangel",
            self.locale_dir,
            languages=[lang],  # FIXME change dir lookup
            fallback=(lang == "en")  # We don't care about EN translations
        )
        self.ugettext = locales.gettext
        self.lang = lang

        # update all the kv rules attached to this text
        for func, largs, kwargs in self.observers:
            func(largs, None, None)
