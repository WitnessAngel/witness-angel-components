# This file is part of Witness Angel Components
# SPDX-FileCopyrightText: Copyright Prolifik SARL
# SPDX-License-Identifier: GPL-2.0-or-later

from devices import dfrobot_epaper  # Must come from DFRobot_RPi_Display_v2 repository

from wacomponents.devices.epaper._epaper_base import EpaperStatusDisplayBase


class DfrobotEpaperStatusDisplay2in13v2(EpaperStatusDisplayBase):

    # SPECIFIC PARAMETERS #

    _RASPBERRY_SPI_BUS = 0
    _RASPBERRY_SPI_DEV = 0
    _RASPBERRY_PIN_CS = 27
    _RASPBERRY_PIN_CD = 17
    _RASPBERRY_PIN_BUSY = 4

    # COMMON PARAMETERS #

    PAPER_WIDTH = 250
    PAPER_HEIGHT = 122

    TEXT_OFFSET_X = 122
    TEXT_OFFSET_Y = 70

    PREVIEW_IMAGE_WIDTH = 120
    PREVIEW_IMAGE_HEIGHT = int(PREVIEW_IMAGE_WIDTH / (16 / 9))

    BUTTON_PIN_1 = 21
    BUTTON_PIN_2 = 20
    BUTTON_PIN_3 = None
    BUTTON_PIN_4 = None

    SMALL_DISPLAY = True

    def __init__(self):
        self.epaper = dfrobot_epaper.DFRobot_Epaper_SPI(
            self._RASPBERRY_SPI_BUS,
            self._RASPBERRY_SPI_DEV,
            self._RASPBERRY_PIN_CS,
            self._RASPBERRY_PIN_CD,
            self._RASPBERRY_PIN_BUSY,
        )

    def _initialize_display(self):
        # Weirdly, no need for _powerOn/_poweroff on this e-paper screen
        self.epaper.begin()

    def _display_image(self, pil_image):
        self._clear_display()
        pil_image.convert("1").save("tempimage.bmp")
        self.epaper.bitmapFile(0, 0, "tempimage.bmp")

    def _clear_display(self):
        self.epaper.clearScreen()
        # self.epaper.readID()

    def _release_display(self):
        # Nothing to do after an update, it seems
        # And at program termination, DFRobot_Epaper_SPI calls RPIGPIO.cleanup() via __del__()
        pass
