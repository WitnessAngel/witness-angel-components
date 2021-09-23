# -*- coding: utf-8 -*-

import gettext
import locale
from gettext import NullTranslations

import kivy
from kivy.lang import Observable


# VERY rough detection of user language, will often not work under Windows but it's OK
# See https://stackoverflow.com/a/25691701 and win32.GetUserDefaultUILanguage()
_lang_code, _charset = locale.getlocale()
DEFAULT_LANGUAGE = "fr" if "fr" in _lang_code.lower() else "en"


def get_package_translator(language, locale_dir):
    return gettext.translation(
        "witnessangel",
        locale_dir,
        languages=[language],
        fallback=True  # (language == "en")  # We don't care about EN translations
    )


class _Translator(Observable):
    """Internationalization of the program, heavily modified from https://github.com/tito/kivy-gettext-example"""

    observers = []
    language = None
    ugettext = None
    locale_dirs = None  # In precedence order

    def __init__(self, default_lang=None, locale_dirs=None):
        super().__init__()
        self.locale_dirs = locale_dirs or []
        self.switch_lang(default_lang)

    def _(self, text):
        return self.ugettext(text)

    def fbind(self, name, func, args, **kwargs):
        if name == "_":
            self.observers.append((func, args, kwargs))
        else:
            return super().fbind(name, func, *args, **kwargs)

    def funbind(self, name, func, args, **kwargs):
        if name == "_":
            key = (func, args, kwargs)
            if key in self.observers:
                self.observers.remove(key)
        else:
            return super().funbind(name, func, *args, **kwargs)

    def add_locale_dirs(self, *locale_dirs):
        self.locale_dirs[0:0] = locale_dirs  # Added AT THE BEGINNING
        self.switch_lang(self.language)

    def switch_lang(self, language):
        if not language or not self.locale_dirs:
            translator = NullTranslations()
        else:
            # Instantiate the whole translator chain
            translator = None
            for locale_dir in self.locale_dirs:
                _translator = get_package_translator(language, locale_dir=locale_dir)
                if translator is None:
                    translator = _translator  # Head of chain
                else:
                    translator.add_fallback(_translator)

        self.ugettext = translator.gettext
        self.language = language

        # update all the kv rules attached to this text
        _obsolete_idx = []

        for idx, (func, largs, kwargs) in enumerate(self.observers):
            try:
                func(largs, None, None)
            except ReferenceError:
                _obsolete_idx.append(idx)

        for _idx in reversed(_obsolete_idx):
            # Reversed loop, to preserve meaning of indexes
            del self.observers[_idx]


tr = _Translator(DEFAULT_LANGUAGE)  # Initially without locale data files
