# -*- coding: utf-8 -*-

import gettext

import kivy
from kivy.lang import Observable

#LOCALE_DIR = Path(__file__).parents[3] / "data" / "locales"
#print("@@@@@@@@@ LOCALE DIR", LOCALE_DIR)


class Lang(Observable):
    """Internationalization of the program : https://github.com/tito/kivy-gettext-example"""

    observers = []
    lang = None

    def __init__(self, defaultlang, locale_dir):
        super(Lang, self).__init__()
        self.ugettext = None
        self.lang = defaultlang
        self.switch_lang(self.lang)
        self.locale_dir = locale_dir

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
            "witness-angel-client",
            self.locale_dir,
            languages=[lang],  # FIXME change dir lookup
        )
        self.ugettext = locales.gettext

        # update all the kv rules attached to this text
        for func, largs, kwargs in self.observers:
            func(largs, None, None)
