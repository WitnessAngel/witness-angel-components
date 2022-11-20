from pathlib import Path

from wacomponents.application.recorder_service import ActivityNotificationType
from wacryptolib.cryptainer import CryptainerEncryptionPipeline


class PreviewImageMixin:

    PREVIEW_IMAGE_WIDTH_PX = 140
    PREVIEW_IMAGE_HEIGHT_PX = 104

    def __init__(self,
                  preview_image_path: Path,
                  **kwargs):
         super().__init__(**kwargs)
         self._preview_image_path = preview_image_path  # Can be empty

    def _do_generate_preview_image(self, output, width_px, height_px):
        raise NotImplementedError("_generate_preview_image() not implemented")

    def _conditionally_regenerate_preview_image(self):
        if self._preview_image_path:

            # Cleanup potential previous preview image
            try:
                self._preview_image_path.unlink()  # FIXME use "missing_ok" soon
            except FileNotFoundError:
                pass

            self._do_generate_preview_image(str(self._preview_image_path),
                                         width_px=self.PREVIEW_IMAGE_WIDTH_PX,
                                         height_px=self.PREVIEW_IMAGE_HEIGHT_PX)

    # HOOK for PeriodicSubprocessStreamRecorder-based sensors
    def _launch_and_consume_subprocess(self, *args, **kwargs):
        self._conditionally_regenerate_preview_image()
        return super()._launch_and_consume_subprocess(*args, **kwargs)


class CryptainerEncryptionPipelineWithRecordingProgressNotification(CryptainerEncryptionPipeline):

    # We send notifications only when a certain amount of bytes was recorded
    PROGRESS_BYTE_THRESHOLD = 100 * 1024

    def __init__(self,
                 *args,
                 recording_progress_notification_callback=None,
                 **kwargs):
        super().__init__(*args, **kwargs)
        assert recording_progress_notification_callback is None or callable(recording_progress_notification_callback), recording_progress_notification_callback
        self._recording_progress_notification_callback = recording_progress_notification_callback
        self._pending_byte_count = 0

    def encrypt_chunk(self, chunk: bytes, *args, **kwargs):
        if self._recording_progress_notification_callback:
            self._pending_byte_count += len(chunk)
            if self._pending_byte_count > self.PROGRESS_BYTE_THRESHOLD:
                self._recording_progress_notification_callback()
                self._pending_byte_count = 0

        return super().encrypt_chunk(chunk, *args, **kwargs)


class ActivityNotificationMixin:
    """To be used mainly with subclass of PeriodicEncryptionStreamMixin"""

    activity_notification_color = None  # RGB tuple, to be overridden in subclass

    def __init__(self,
                 *args,
                 activity_notification_callback,
                 **kwargs):
        super().__init__(*args, **kwargs)
        assert self.activity_notification_color, "missing activity_notification_color"
        print(">>>>>>>>>>>>>>> SETTING UP _activity_notification_callback", activity_notification_callback)
        self._activity_notification_callback = activity_notification_callback

    def _get_cryptainer_encryption_stream_creation_kwargs(self) -> dict:
        recording_progress_notification_callback = lambda: self._activity_notification_callback(
                    notification_type=ActivityNotificationType.RECORDING_PROGRESS,
                    notification_color=self.activity_notification_color)
        return {"cryptainer_encryption_stream_class": CryptainerEncryptionPipelineWithRecordingProgressNotification,
                "cryptainer_encryption_stream_extra_kwargs": {
                    "recording_progress_notification_callback": recording_progress_notification_callback}}
