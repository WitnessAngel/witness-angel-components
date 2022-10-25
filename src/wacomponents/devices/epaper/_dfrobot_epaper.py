from devices import dfrobot_epaper

from wacomponents.devices.epaper._epaper_base import EpaperStatusDisplayBase


class DfrobotEpaperStatusDisplay(EpaperStatusDisplayBase):

    # SPECIFIC PARAMETERS #

    _RASPBERRY_SPI_BUS = 0
    _RASPBERRY_SPI_DEV = 0
    _RASPBERRY_PIN_CS = 27
    _RASPBERRY_PIN_CD = 17
    _RASPBERRY_PIN_BUSY = 4

    epaper = dfrobot_epaper.DFRobot_Epaper_SPI(
        _RASPBERRY_SPI_BUS, _RASPBERRY_SPI_DEV, _RASPBERRY_PIN_CS, _RASPBERRY_PIN_CD, _RASPBERRY_PIN_BUSY)

    # COMMON PARAMETERS #

    PAPER_WIDTH = 250
    PAPER_HEIGHT = 122

    TEXT_OFFSET_X = 122
    TEXT_OFFSET_Y = 70

    PREVIEW_IMAGE_WIDTH = 120
    PREVIEW_IMAGE_HEIGHT = int(PREVIEW_IMAGE_WIDTH / (16/9))

    BUTTON_PIN_1 = 21
    BUTTON_PIN_2 = 20
    BUTTON_PIN_3 = None
    BUTTON_PIN_4 = None

    SMALL_DISPLAY = True

    def _initialize_display(self):
        self.epaper.begin()

    def _clear_screen(self):
        self.epaper.clearScreen()
        #self.epaper.readID()

    def _display_image(self, pil_image):
        self._clear_screen()
        pil_image.convert('1').save("tempimage.bmp")
        self.epaper.bitmapFile(0, 0, "tempimage.bmp")

    def _release_display(self):
        pass  # Nothing to do, since DFRobot_Epaper_SPI calls RPIGPIO.cleanup() on __del__()
