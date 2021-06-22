from PIL import ImageFont
from pathlib import Path
from waguilib.epaper._base import EpaperStatusDisplayBase
from waveshare_epd import epd2in7


FONT_PATH = str(Path(__file__).parent.joinpath('Font.ttc'))


class WaveshareEpaperStatusDisplay(EpaperStatusDisplayBase):

    epd = epd2in7.EPD() # get the display

    YDOT = epd2in7.EPD_HEIGHT
    XDOT = epd2in7.EPD_WIDTH

    Xbasic = 140
    Ybasic = 100

    Ximage_size = 140
    Yimage_size = 98

    screen_image = ""
    finale_image = ""

    status_obj = "test"

    fontFilePath = ImageFont.truetype(FONT_PATH, 24)

    def initialization(self):
        self.epd.init()           # initialize the display
        self.epd.Clear(0xFF)      # clear the display

    def _display_image(self, pil_image):
        self.initialization()
        Himage = self.display_status(self.screen_image, self.Ximage_size, self.Yimage_size, self.finale_image, self.epd, self.YDOT, self.XDOT, self.fontFilePath, self.Ybasic, self.Xbasic, self.status_obj)
        self.epd.display(self.epd.getbuffer(Himage))
