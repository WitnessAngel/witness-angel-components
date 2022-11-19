from pathlib import Path

from wacryptolib.cryptainer import CryptainerEncryptionPipeline


class PreviewImageMixin:

    PREVIEW_IMAGE_WIDTH_PX = 140
    PREVIEW_IMAGE_HEIGHT_PX = 104

    def __init__(self,
                  preview_image_path: Path,
                  **kwargs):
         super().__init__(**kwargs)
         self._preview_image_path = preview_image_path  # Can be empty

    def _generate_preview_image(self, output_path, width_px, height_px):
        raise NotImplementedError("_generate_preview_image() not implemented")

    def _launch_and_consume_subprocess(self, *args, **kwargs):

        if self._preview_image_path:

            # Cleanup potential previous preview image
            try:
                self._preview_image_path.unlink()  # FIXME use "missing_ok" soon
            except FileNotFoundError:
                pass

            self._generate_preview_image(self._preview_image_path,
                                         width_px=self.PREVIEW_IMAGE_WIDTH_PX,
                                         height_px=self.PREVIEW_IMAGE_HEIGHT_PX)

        return super()._launch_and_consume_subprocess(*args, **kwargs)


class CryptainerEncryptionPipelineWithActivityNotification(CryptainerEncryptionPipeline):

    def __init__(self,
                 *args,
                 activity_notification_callback=None,
                 **kwargs):
        super().__init__(*args, **kwargs)
        assert activity_notification_callback is None or callable(activity_notification_callback), activity_notification_callback
        self._activity_notification_callback = activity_notification_callback

    def encrypt_chunk(self, *args, **kwargs):
        if self._activity_notification_callback:
            self._activity_notification_callback()
        return super().encrypt_chunk(*args, **kwargs)


class ActivityNotificationMixin:

    activity_notification_color = None  # RGB tuple, to be overridden in subclass

    def __init__(self,
                 *args,
                 activity_notification_callback,
                 **kwargs):
        super().__init__(*args, **kwargs)
        assert self.activity_notification_color
        print(">>>>>>>>>>>>>>> SETTING UP _activity_notification_callback", activity_notification_callback)
        self._activity_notification_callback = lambda: activity_notification_callback(self.activity_notification_color)

    def _get_cryptainer_encryption_stream_creation_kwargs(self) -> dict:
        return {"cryptainer_encryption_stream_class": CryptainerEncryptionPipelineWithActivityNotification,
                "cryptainer_encryption_stream_extra_kwargs": {"activity_notification_callback": self._activity_notification_callback}}
