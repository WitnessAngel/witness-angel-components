import os
from PIL import Image, ImageDraw, ImageFont


###THIS_DIR = Path(__file__).parent
from kivy.resources import resource_find


class EpaperStatusDisplayBase:

    font_size = 14  # Pixels
    line_height = 15  # Pixels

    # Override these in subclasses to enable GPIO-BCM buttons
    BUTTON_PIN_1 = None
    BUTTON_PIN_2 = None
    BUTTON_PIN_3 = None
    BUTTON_PIN_4 = None

    def __init__(self, **options):
        pass

    def get_font(self, font_file_path, font_size):
        font = ImageFont.truetype(font_file_path, font_size)
        return font

    def get_blank_frame(self):
        image = Image.new('L', (self.PAPER_WIDTH, self.PAPER_HEIGHT), 255)  # Monochrome
        return image

    def get_blank_thumbnail(self):
        image = Image.new('L', (self.PREVIEW_IMAGE_WIDTH, self.PREVIEW_IMAGE_HEIGHT), 255)  # Monochrome
        return image

    def _convert_to_preview_image(self, preview_image_path, thumbnail_image_dimensions, thumbnail_image_path):
        """Convert source image to a Greyshade preview thumbnail stored on disk."""
        try:
            img = Image.open(preview_image_path)
            img = img.resize(thumbnail_image_dimensions)
            image_gray = img.convert('L')
            image_gray.save(thumbnail_image_path)
        except FileNotFoundError:
            pass  # Preview image not (yet) generated, it's OK

    def initialize_display(self):
        self._initialize_display()

    def release_display(self):
        self._release_display()

    def _initialize_display(self):
        """Prepare e-parer for display"""
        raise NotImplementedError("_initialize_display() not implemented")

    def _release_display(self):
        """Shutdown display, e.g. to avoid harming it by too long power-ON"""
        raise NotImplementedError("_release_display() not implemented")

    def _display_image(self, screen_image):
        """Directly output image to device"""
        raise NotImplementedError("_display_image() not implemented")

    def display_status(self, status_obj, preview_image_path, text_offset_x=None, text_offset_y=None, font_file_path=None):
        assert isinstance(preview_image_path, str), preview_image_path

        text_offset_x = text_offset_x if text_offset_x is not None else self.TEXT_OFFSET_X
        text_offset_y = text_offset_y if text_offset_y is not None else self.TEXT_OFFSET_Y
        #source_image_path = source_image_path or str(THIS_DIR / "preview.png")
        font_file_path = font_file_path or resource_find("fonts/epaper_font.ttc")
        assert font_file_path, font_file_path

        thumbnail_image_path = preview_image_path + ".thumb.jpg"
        try:
            os.unlink(thumbnail_image_path)
        except FileNotFoundError:
            pass

        self._convert_to_preview_image(preview_image_path,
                                       thumbnail_image_dimensions=(self.PREVIEW_IMAGE_WIDTH, self.PREVIEW_IMAGE_HEIGHT),
                                       thumbnail_image_path=thumbnail_image_path)

        # Create big image to display on EPaper
        framebuffer = self.get_blank_frame()

        try:
            thumbnail_image = Image.open(thumbnail_image_path)
        except FileNotFoundError:
            thumbnail_image = self.get_blank_thumbnail()

        framebuffer.paste(thumbnail_image, (0,0))
        font = self.get_font(font_file_path, font_size=self.font_size)
        draw = ImageDraw.Draw(framebuffer)

        # Print recording status
        draw.text((text_offset_x, 0), "Recording", font = font, fill = 0)
        #draw.rectangle(((text_offset_x + 60), 1, (text_offset_x + 125), self.line_height), fill = 0)
        draw.text(((text_offset_x + 68), 0), status_obj.pop("recording_status"), font = font, fill = 1)

        # Print bitmap wifi logo and status
        wifi_logo = Image.open(resource_find("images/wifi.bmp"))
        bmp = wifi_logo.resize((20, 15))
        framebuffer.paste(bmp, (text_offset_x, 20))
        draw.text(((text_offset_x + 25), 20), status_obj.pop("wifi_status"), font = font, fill = 0)

        ethernet_logo = Image.open(resource_find("images/ethernet_small.bmp"))
        bmp = ethernet_logo.resize((20, 20))
        framebuffer.paste(bmp, (text_offset_x + 60, 20))
        draw.text(((text_offset_x + 85), 20), status_obj.pop("ethernet_status"), font = font, fill = 0)

        # Print datetime
        now_datetime = status_obj.pop("now_datetime")
        now_date = now_datetime.strftime("%Y/%m/%d")
        now_hour = now_datetime.strftime("%H:%M:%S")

        draw.text((text_offset_x, 40), now_date, font = font, fill = 0)
        draw.text((text_offset_x, (40 + self.line_height)), now_hour, font = font, fill = 0)

        for idx, (key, value) in enumerate(status_obj.items()):
            #print(">>>>", idx, key, value)
            label = key.replace("_", " ").title()
            draw.text((1, (text_offset_y + idx * self.line_height)), label, font = font, fill = 0)
            draw.text(((1 + 120), (text_offset_y + idx * self.line_height)), value, font = font, fill = 0)
            """
            # Print Disk status
            draw.text((text_offset_x, text_offset_y), "Disk Left", font = font, fill = 0)
            draw.text(((text_offset_x + 100), text_offset_y), status_obj, font = font, fill = 0)
    
            # Print RAM status
            draw.text((text_offset_x, (text_offset_y + self.line_height)), "RAM Left", font = font, fill = 0)
            draw.text(((text_offset_x + 100), (text_offset_y + self.line_height)), status_obj, font = font, fill = 0)
    
            # Print Containers status
            draw.text((text_offset_x, (text_offset_y + (self.line_height * 2))), "Containers", font = font, fill = 0)
            draw.text(((text_offset_x + 100), (text_offset_y + (self.line_height * 2))), status_obj, font = font, fill = 0)
            """
        self._display_image(framebuffer)
