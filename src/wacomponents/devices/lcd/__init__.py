LCD_TYPES = ["waveshare_1.3_lcd"]


def get_lcd_instance(lcd_type):
    if lcd_type == LCD_TYPES[0]:
        from ._waveshare_lcd import WaveshareLcdDisplay1in3

        return WaveshareLcdDisplay1in3()
    else:
        raise ValueError("Unknown lcd type %r" % lcd_type)
