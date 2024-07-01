# This file is part of Witness Angel Components
# SPDX-FileCopyrightText: Copyright Prolifik SARL
# SPDX-License-Identifier: GPL-2.0-or-later

from pathlib import Path

from waveshare_epd import epd2in7, epd2in13_V3

from wacomponents.devices.epaper._epaper_base import EpaperStatusDisplayBase

FONT_PATH = str(Path(__file__).parent.joinpath("Font.ttc"))  # FIXME put assets elsewhere


class WaveshareEpaperStatusDisplayBase(EpaperStatusDisplayBase):

    # Subclass must define self.epd! #

    def _initialize_display(self):
        self.epd.init()

    def _display_image(self, pil_image):
        # self._clear_display()
        pil_image.convert("1")  # Most screens don't support levels of grey
        self.epd.display(self.epd.getbuffer(pil_image))

    def _clear_display(self):
        self.epd.Clear(0xFF)

    def _release_display(self):
        self.epd.sleep()  # IMPORTANT, else the display can be damaged by long power-on


class WaveshareEpaperStatusDisplay2in7(WaveshareEpaperStatusDisplayBase):

    # INVERTED, since we want landscape orientation!
    PAPER_WIDTH = epd2in7.EPD_HEIGHT
    PAPER_HEIGHT = epd2in7.EPD_WIDTH

    TEXT_OFFSET_X = 141
    TEXT_OFFSET_Y = 80

    # FIXME rename to "thumbnail" stuffs"
    PREVIEW_IMAGE_WIDTH = 140
    PREVIEW_IMAGE_HEIGHT = int(PREVIEW_IMAGE_WIDTH / (16 / 9))

    BUTTON_PIN_1 = 5
    BUTTON_PIN_2 = 6
    BUTTON_PIN_3 = 13
    BUTTON_PIN_4 = 19

    def __init__(self):
        self.epd = epd2in7.EPD()

    def _initialize_display(self):
        self.epd.Init_4Gray()

    def _display_image(self, pil_image):
        self.epd.display_4Gray(self.epd.getbuffer_4Gray(pil_image))


class WaveshareEpaperStatusDisplay2in13V3(WaveshareEpaperStatusDisplayBase):

    # INVERTED, since we want landscape orientation!
    PAPER_WIDTH = epd2in13_V3.EPD_HEIGHT
    PAPER_HEIGHT = epd2in13_V3.EPD_WIDTH

    TEXT_OFFSET_X = 122
    TEXT_OFFSET_Y = 70

    PREVIEW_IMAGE_WIDTH = 120
    PREVIEW_IMAGE_HEIGHT = int(PREVIEW_IMAGE_WIDTH / (16 / 9))

    # No BUTTON_PIN_X on this screen, so leave them as "None"

    SMALL_DISPLAY = True

    def __init__(self):
        self.epd = epd2in13_V3.EPD()
