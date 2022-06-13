# -*- coding: utf-8 -*-

import gettext
from gettext import NullTranslations

import locale
import os
from kivy.lang import Observable

from wacomponents.default_settings import IS_ANDROID, IS_IOS


def detect_default_language():
    """Rough language detection on multiple platforms

    One can FORCE the GUI language with "LANG" environment variable.
    """
    ALLOWED_LANGUAGES = ["en", "fr"]

    _normalize = lambda x: x.strip().lower()

    lang_code = ALLOWED_LANGUAGES[0]

    forced_lang_code = _normalize(os.environ.get("LANG", ""))
    if forced_lang_code in ALLOWED_LANGUAGES:  # We don't deal with advanced forms like "en_US.UTF-8"...
        return forced_lang_code

    if IS_ANDROID:
        try:
            from jnius import autoclass
            JavaUtilLocale = autoclass('java.util.Locale')
            java_locale = JavaUtilLocale.getDefault()
            lang_code = java_locale.language
            #print("######### JAVA LOCALE DETECTED: %s %s #########" % (java_locale.language, java_locale.country ))
        except Exception as exc:
            print("######### JavaUtilLocale exception %r" % exc)  # FIXME use logging
    elif IS_IOS:
        try:
            import pyobjus
            NSLocale = pyobjus.autoclass("NSLocale")
            languages = NSLocale.preferredLanguages()
            lang_code = languages.objectAtIndex_(0).UTF8String().decode("utf-8")  # Might include region code too
            #print("######### APPLE LOCALE DETECTED: %s #########" % lang_code)
        except Exception as exc:
            print("######### NSLocale exception %r" % exc)  # FIXME use logging
    else:
        # VERY rough detection of user language, will often not work under Windows but it's OK
        # See https://stackoverflow.com/a/25691701 and win32.GetUserDefaultUILanguage()
        lang_code, _charset = locale.getlocale()
        #print("######### DEFAULT LOCALE DETECTED: %s %s #########" % (lang_code, _charset))

    lang_code = lang_code or ""  # lang_code might be None if undetected
    return "fr" if _normalize(lang_code).startswith("fr") else "en"

DEFAULT_LANGUAGE = detect_default_language()


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

    @staticmethod
    def f(string):
        """
        Helper to translate fstring-style constructs, using KEYWORD placeholders::

            variable = "SOMETHING"
            tr.f(tr._("My {variable}"))
        """
        from inspect import currentframe
        from copy import copy
        frame = currentframe().f_back
        kwargs = copy(frame.f_globals)
        kwargs.update(frame.f_locals)
        return string.format(**kwargs)


tr = _Translator(DEFAULT_LANGUAGE)  # Initially without locale data files
