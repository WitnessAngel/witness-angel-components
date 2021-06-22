from waguilib.epaper._base import EpaperStatusDisplayBase
from devices import dfrobot_epaper

class DfrobotEpaperStatusDisplay(EpaperStatusDisplayBase):


    # peripheral params
    RASPBERRY_SPI_BUS = 0
    RASPBERRY_SPI_DEV = 0
    RASPBERRY_PIN_CS = 27
    RASPBERRY_PIN_CD = 17
    RASPBERRY_PIN_BUSY = 4

    epaper = dfrobot_epaper.DFRobot_Epaper_SPI(RASPBERRY_SPI_BUS, RASPBERRY_SPI_DEV, RASPBERRY_PIN_CS, RASPBERRY_PIN_CD, RASPBERRY_PIN_BUSY) # create epaper object

    XDOT = 128
    YDOT = 250

    Xbasic = 125
    Ybasic = 60

    Ximage_size = 120
    Yimage_size = 78

    screen_image = ""
    finale_image = ""

    fontFilePath = "../../display_extension/wqydkzh.ttf" # fonts file

    status_obj = "test"

    def initialization(self):
        self.epaper.begin()
        self.epaper.clearScreen()
        #self.epaper.readID()

    def _display_image(self, pil_image):
        self.initialization()
        Himage = self.display_status(self.screen_image, self.Ximage_size, self.Yimage_size, self.finale_image, self.epaper, self.YDOT, self.XDOT, self.fontFilePath, self.Ybasic, self.Xbasic, self.status_obj)
        Himage.save(pil_image)
        self.epaper.bitmapFile(0, 0, pil_image)
