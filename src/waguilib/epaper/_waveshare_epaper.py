from PIL import ImageFont
from pathlib import Path
from waguilib.epaper._base import EpaperStatusDisplayBase
from waveshare_epd import epd2in7


FONT_PATH = str(Path(__file__).parent.joinpath('Font.ttc'))  # FIXME put assets elsewhere


class WaveshareEpaperStatusDisplay(EpaperStatusDisplayBase):

    epd = epd2in7.EPD() # get the display

    PAPER_WIDTH = epd2in7.EPD_WIDTH
    PAPER_HEIGHT = epd2in7.EPD_HEIGHT

    TEXT_OFFSET_X = 140
    TEXT_OFFSET_Y = 100

    PREVIEW_IMAGE_WIDTH = 140
    PREVIEW_IMAGE_HEIGHT = 98

    #screen_image = ""
    #finale_image = ""

    fontFilePath = ImageFont.truetype(FONT_PATH, 24)

    def initialize(self):
        self.epd.init()           # initialize the display
        #self.epd.Clear(0xFF)      # clear the display
        #self.epd.sleep()

    def _display_image(self, pil_image):
        #self.initialization()
        #Himage = self.display_status(self.screen_image, self.PREVIEW_IMAGE_WIDTH, self.PREVIEW_IMAGE_HEIGHT, self.finale_image, self.epd,#self.PAPER_HEIGH, self.PAPER_WIDTH, self.fontFilePath, self.text_offset_y, self.text_offset_x, self.status_obj)
        self.epd.display(self.epd.getbuffer(pil_image))
