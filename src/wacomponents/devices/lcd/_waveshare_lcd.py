import spidev as SPI
import ST7789

from PIL import Image, ImageDraw, ImageFont

# Raspberry Pi pin configuration:
RST = 27
DC = 25
BL = 24
bus = 0
device = 0


class WaveshareImageDisplay1in3:

    def __init__(self):
        lcd_display = ST7789.ST7789(SPI.SpiDev(bus, device),RST, DC, BL)
        lcd_display.Init()
        self.lcd_display = lcd_display
        self.clear()

    def display_image(self, image):
        thumbnail_size = (self.lcd_display.width, self.lcd_display.height)
        image.thumbnail(thumbnail_size, Image.ANTIALIAS)  # Modifies IN PLACE
        thumbnail_image = Image.new('RGB', thumbnail_size, (0, 0, 0))
        thumbnail_image.paste(
            image, (int((thumbnail_size[0] - image.size[0]) // 2), int((thumbnail_size[1] - image.size[1]) // 2))
        )
        self.lcd_display.ShowImage(thumbnail_image, 0, 0)

    def clear(self):
        self.lcd_display.clear()
