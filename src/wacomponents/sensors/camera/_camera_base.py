from pathlib import Path


class PreviewImageMixin:

    PREVIEW_IMAGE_WIDTH_PX = 140
    PREVIEW_IMAGE_HEIGHT_PX = 104

    def __init__(self,
                  preview_image_path: Path,
                  **kwargs):
         super().__init__(**kwargs)
         self._preview_image_path = preview_image_path  # Can be empty

    def _launch_and_consume_subprocess(self, *args, **kwargs):

        if self._preview_image_path:
            # Cleanup potential previous preview image
            try:
                self._preview_image_path.unlink()  # FIXME use "missing_ok" soon
            except FileNotFoundError:
                pass

        return super()._launch_and_consume_subprocess( *args, **kwargs)
