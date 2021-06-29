import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

THIS_DIR = Path(__file__).parent

class EpaperStatusDisplayBase:

    font_size = 18
    line_height = 20  # Pixels

    extended_mode = False

    def __init__(self, **options):
        pass

    def get_font(self, font_file_path, font_size):
        font = ImageFont.truetype(font_file_path, font_size)
        return font

    def get_blank_frame(self):
        image = Image.new('1', (self.PAPER_HEIGHT, self.PAPER_WIDTH), 255)  # Monochrome
        return image

    def _convert_to_preview_image(self, source_image_path, preview_image_dimensions, preview_image_path):
        """Convert source image to a Greyshade preview thumbnail stored on disk."""
        img = Image.open(source_image_path)
        img = img.resize(preview_image_dimensions)
        image_gray = img.convert('L')
        image_gray.save(preview_image_path)

    def _display_image(self, screen_image):
        """Directly output image to device"""
        raise NotImplementedError("_display_image() not implemented")

    def display_status(self, status_obj, text_offset_x=None, text_offset_y=None, source_image_path=None, font_file_path=None):

        text_offset_x = text_offset_x if text_offset_x is not None else self.TEXT_OFFSET_X
        text_offset_y = text_offset_y if text_offset_y is not None else self.TEXT_OFFSET_Y
        source_image_path = source_image_path or str(THIS_DIR / "preview.png")
        font_file_path = font_file_path or str(THIS_DIR / "Font.ttc")

        preview_image_path = source_image_path + ".thumb.jpg"
        self._convert_to_preview_image(source_image_path, preview_image_dimensions=(self.PREVIEW_IMAGE_WIDTH, self.PREVIEW_IMAGE_HEIGHT), preview_image_path=preview_image_path)
        preview_image = Image.open(preview_image_path)

        # Create big image to display on EPaper
        framebuffer = self.get_blank_frame()
        framebuffer.paste(preview_image, (0,0))
        font = self.get_font(font_file_path, font_size=self.font_size)

        # Print datetime
        now = datetime.datetime.now()
        now_date = now.strftime("%Y/%m/%d")
        now_hour = now.strftime("%H:%M:%S")
        draw = ImageDraw.Draw(framebuffer)
        draw.text((1, (text_offset_y + self.line_height)), now_date, font = font, fill = 0)
        draw.text((1, (text_offset_y + (self.line_height * 2))), now_hour, font = font, fill = 0)

        # Print record status
        draw.text((text_offset_x, 0), "Record", font = font, fill = 0)
        draw.rectangle(((text_offset_x + 60), 1, (text_offset_x + 125), self.line_height), fill = 0)
        draw.text(((text_offset_x + 61), 0), status_obj, font = font, fill = 1)

        # Print bitmap wifi logo and status
        wifi_logo = Image.open(str(THIS_DIR.joinpath('wifi.bmp')))
        bmp = wifi_logo.resize((20, 15))
        framebuffer.paste(bmp, (text_offset_x, 28))
        draw.text(((text_offset_x + 25), 30), status_obj, font = font, fill = 0)

        # Print Disk status
        draw.text((text_offset_x, text_offset_y), "Disk Left", font = font, fill = 0)
        draw.text(((text_offset_x + 100), text_offset_y), status_obj, font = font, fill = 0)

        # Print RAM status
        draw.text((text_offset_x, (text_offset_y + self.line_height)), "RAM Left", font = font, fill = 0)
        draw.text(((text_offset_x + 100), (text_offset_y + self.line_height)), status_obj, font = font, fill = 0)

        # Print Containers status
        draw.text((text_offset_x, (text_offset_y + (self.line_height * 2))), "Containers", font = font, fill = 0)
        draw.text(((text_offset_x + 100), (text_offset_y + (self.line_height * 2))), status_obj, font = font, fill = 0)

        self._display_image(framebuffer)
