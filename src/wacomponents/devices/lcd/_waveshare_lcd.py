import spidev as SPI
from PIL import Image
from PIL.Image import Image

from . import ST7789

# Raspberry Pi pin configuration:
RST = 27
DC = 25
BL = 24
bus = 0
device = 0


KEY_UP_PIN = 6
KEY_DOWN_PIN = 19
KEY_LEFT_PIN = 5
KEY_RIGHT_PIN = 26
KEY_PRESS_PIN = 13

KEY1_PIN = 21
KEY2_PIN = 20
KEY3_PIN = 16


class WaveshareLcdDisplay1in3:

    BUTTON_PIN_1 = KEY1_PIN
    BUTTON_PIN_2 = KEY2_PIN
    BUTTON_PIN_3 = KEY3_PIN
    BUTTON_PIN_4 = None

    def __init__(self):
        lcd_display = ST7789.ST7789(SPI.SpiDev(bus, device), RST, DC, BL)
        lcd_display.Init()
        self.lcd_display = lcd_display
        self.clear()

    def display_image(self, image: Image):
        thumbnail_size = (self.lcd_display.width, self.lcd_display.height)
        image.thumbnail(thumbnail_size, Image.ANTIALIAS)  # Modifies IN PLACE
        thumbnail_image = Image.new("RGB", thumbnail_size, (0, 0, 0))
        thumbnail_image.paste(
            image, (int((thumbnail_size[0] - image.size[0]) // 2), int((thumbnail_size[1] - image.size[1]) // 2))
        )
        self.lcd_display.ShowImage(thumbnail_image, 0, 0)

    def clear(self):
        self.lcd_display.clear()
