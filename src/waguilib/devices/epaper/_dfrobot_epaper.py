from waguilib.devices.epaper._epaper_base import EpaperStatusDisplayBase
from devices import dfrobot_epaper

class DfrobotEpaperStatusDisplay(EpaperStatusDisplayBase):


    # peripheral params
    RASPBERRY_SPI_BUS = 0
    RASPBERRY_SPI_DEV = 0
    RASPBERRY_PIN_CS = 27
    RASPBERRY_PIN_CD = 17
    RASPBERRY_PIN_BUSY = 4

    epaper = dfrobot_epaper.DFRobot_Epaper_SPI(RASPBERRY_SPI_BUS, RASPBERRY_SPI_DEV, RASPBERRY_PIN_CS, RASPBERRY_PIN_CD, RASPBERRY_PIN_BUSY) # create epaper object

    PAPER_WIDTH = 128
    PAPER_HEIGHT = 250

    TEXT_OFFSET_X = 125
    TEXT_OFFSET_Y = 60

    PREVIEW_IMAGE_WIDTH = 120
    PREVIEW_IMAGE_HEIGHT = 78

    screen_image = ""
    finale_image = ""

    fontFilePath = "../../display_extension/wqydkzh.ttf" # fonts file

    status_obj = "test"

    BUTTON_PIN_1 = 21
    BUTTON_PIN_2 = 20


    def initialization(self):
        self.epaper.begin()
        self.epaper.clearScreen()
        #self.epaper.readID()

    def _display_image(self, pil_image):
        self.initialization()
        Himage = self.display_status(self.screen_image, self.PREVIEW_IMAGE_WIDTH, self.PREVIEW_IMAGE_HEIGHT, self.finale_image, self.epaper, self.PAPER_HEIGHT, self.PAPER_WIDTH, self.fontFilePath, self.TEXT_OFFSET_Y, self.TEXT_OFFSET_X, self.status_obj)
        Himage.save(pil_image)
        self.epaper.bitmapFile(0, 0, pil_image)
