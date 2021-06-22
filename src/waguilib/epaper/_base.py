import datetime
from PIL import Image, ImageDraw, ImageFont


class EpaperStatusDisplayBase:

    font_size = 18
    line_height = 20  # Pixels

    extended_mode = False

    def __init__(self, **options):
        pass

    def define_font(self, font_file_path, font_size):
        font = ImageFont.truetype(font_file_path, font_size)
        return font

    def clear_frame(self, epaper_type, YDOT, XDOT):
        image = Image.new('1', (epaper_type.YDOT, epaper_type.XDOT), 255)
        return image

    def convert_and_display_image(self, screen_image, Ximage_size, Yimage_size, finale_image):
        """Convert and display target image on E-paper"""
        img = Image.open(screen_image)
        size = (Ximage_size, Yimage_size)
        img = img.resize(size)
        image_gray = img.convert('L')
        image_gray.save(finale_image)
        return finale_image

    def _display_image(self, screen_image):
        """Directly output image to device"""
        raise NotImplementedError("_display_image() not implemented")

    def display_status(self, screen_image, Ximage_size, Yimage_size, finale_image, epaper_type, YDOT, XDOT, font_file_path, Ybasic, Xbasic, status_obj):
        # Construire l'image avec les valeurs de status_obj, puis l'envoyer ‡ display_image
        image_print = self.convert_and_display_image(screen_image, Ximage_size, Yimage_size, finale_image)
        bmp = Image.open(image_print)
        Himage = self.clear_frame(epaper_type, YDOT, XDOT)
        Himage.paste(bmp, (0,0))
        font18 = self.define_font(font_file_path, self.font_size)

        # Print date
        date = datetime.datetime.now()
        date_to_print = str(date.day)+"/"+str(date.month)+"/"+str(date.year)
        hour_to_print = str(date.hour)+"h"+str(date.minute)+"m"+str(date.second)+"s"
        draw = ImageDraw.Draw(Himage)
        draw.text((1, (Ybasic + self.line_height)), date_to_print, font = font18, fill = 0)
        draw.text((1, (Ybasic + (self.line_height * 2))), hour_to_print, font = font18, fill = 0)

        # Print record status
        draw.text((Xbasic, 0), "Record", font = font18, fill = 0)
        draw.rectangle(((Xbasic + 60), 1, (Xbasic + 125), self.line_height), fill = 0)
        draw.text(((Xbasic + 61), 0), status_obj, font = font18, fill = 1)

        # Print bitmap wifi logo and wifi status
        bmp = Image.open('./wifi.bmp')
        size = (20, 15)
        bmp = bmp.resize(size)
        Himage.paste(bmp, (Xbasic, 28))
        draw.text(((Xbasic + 25), 30), status_obj, font = font18, fill = 0)

        # Print disk statement
        draw.text((Xbasic, Ybasic), "Disk Left", font = font18, fill = 0)
        draw.text(((Xbasic + 100), Ybasic), status_obj, font = font18, fill = 0)

        # Print RAM statement
        draw.text((Xbasic, (Ybasic + self.line_height)), "RAM Left", font = font18, fill = 0)
        draw.text(((Xbasic + 100), (Ybasic + self.line_height)), status_obj, font = font18, fill = 0)

        # Print Containers statement
        draw.text((Xbasic, (Ybasic + (self.line_height * 2))), "Containers", font = font18, fill = 0)
        draw.text(((Xbasic + 100), (Ybasic + (self.line_height * 2))), status_obj, font = font18, fill = 0)
        return Himage
