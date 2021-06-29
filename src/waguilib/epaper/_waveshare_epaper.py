
from pathlib import Path
from waguilib.epaper._epaper_base import EpaperStatusDisplayBase
from waveshare_epd import epd2in7


FONT_PATH = str(Path(__file__).parent.joinpath('Font.ttc'))  # FIXME put assets elsewhere


class WaveshareEpaperStatusDisplay(EpaperStatusDisplayBase):

    # INVERTED, since we want landscape orientation!
    PAPER_WIDTH = epd2in7.EPD_HEIGHT
    PAPER_HEIGHT = epd2in7.EPD_WIDTH

    TEXT_OFFSET_X = 141
    TEXT_OFFSET_Y = 80

    PREVIEW_IMAGE_WIDTH = 140
    PREVIEW_IMAGE_HEIGHT = int(PREVIEW_IMAGE_WIDTH / (16/9))

    def __init__(self):
        self.epd = epd2in7.EPD()

    def _initialize_display(self):
        self.epd.Init_4Gray()
        #self.epd.Clear(0xFF)  # clear the display

    def _display_image(self, pil_image):
        self.epd.display_4Gray(self.epd.getbuffer_4Gray(pil_image))

    def _release_display(self):
        self.epd.sleep()


