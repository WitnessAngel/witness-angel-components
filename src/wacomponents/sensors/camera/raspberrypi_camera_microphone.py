import logging
import subprocess
from subprocess import CalledProcessError, TimeoutExpired
from typing import Optional

import io
import multitimer
from PIL import Image

from wacomponents.application.recorder_service import ActivityNotificationType
from wacomponents.sensors.camera._camera_base import PreviewImageMixin, ActivityNotificationMixin
from wacryptolib.cryptainer import CryptainerEncryptionPipeline
from wacryptolib.sensor import PeriodicSubprocessStreamRecorder, PeriodicEncryptionStreamMixin, PeriodicSensorRestarter
from wacryptolib.utilities import synchronized, catch_and_log_exception

logger = logging.getLogger(__name__)


def list_pulseaudio_microphone_names():
    """Equivalent to command:  pactl list | grep -A2 'Source #' | grep 'Name:'
    """
    import pulsectl

    pulse = pulsectl.Pulse("witness-angel-device")
    results = pulse.source_list()
    source_names = [res.name for res in results]
    # We ignore "sink monitors" (e.g. HDMI output monitor) useless for us
    microphone_names = [name for name in source_names if "input" in name.lower()]
    # print(">>>>>>>>PULSECTL microphone_names IS", microphone_names)
    return microphone_names


def is_legacy_rpi_camera_enabled():
    try:
        output = subprocess.check_output(["vcgencmd", "get_camera"], text=True)
        return "supported=1 " in output
    except CalledProcessError:
        return False


class RaspberryRaspividSensor(PreviewImageMixin, ActivityNotificationMixin, PeriodicSubprocessStreamRecorder):
    """
    Records a raw h264 file using legacy (GPU-based) raspivid interface of the Raspberry Pi.

    No audio can be recorded through this sensor.

    Records a screenshot before each video clip, if requested (this can be slow).
    """

    sensor_name = "rpi_raspivid_camera"
    activity_notification_color = (0, 0, 150)
    record_extension = ".h264"

    def __init__(self, raspivid_parameters: list, **kwargs):
        super().__init__(**kwargs)
        self._raspivid_parameters = raspivid_parameters

    def _do_generate_preview_image(self, output, width_px, height_px):
        assert isinstance(output, str), output

        try:
            snapshot_command_line = [
                "raspistill",
                "--nopreview",  # No GUI display
                "--output",
                output,
                "--width",
                str(width_px),
                "--height",
                str(height_px),
                "--quality",
                "90",
                "-v",
            ]
            logger.debug(
                "Taking camera snapshot with command: %s", " ".join(snapshot_command_line)
            )  # Fixme standardize this
            subprocess.check_call(snapshot_command_line, timeout=20)
        except (CalledProcessError, TimeoutExpired) as exc:
            logger.warning("Couldn't generate screenshot in %s sensor: %s", self.sensor_name, exc)

    def _build_subprocess_command_line(self):

        raspivid_command_line_base = ["raspivid", "--timeout", "0", "--nopreview", "-v"]  # NO timeout

        if self._raspivid_parameters:
            raspivid_parameters = self._raspivid_parameters
        else:
            raspivid_parameters = [
                "--framerate",
                "30",
                "-pf",
                "baseline",  # H264 profile tweaking, lots of other options exist
                # Set most common medium mode for V1 (OV5647) and V2 (IMX219) cameras
                # See https://www.waveshare.com/wiki/RPi_Camera
                "--width",
                "1296",
                "--height",
                "730",
                "--output",
                "-",
            ]

        raspivid_command_line = raspivid_command_line_base + raspivid_parameters
        return raspivid_command_line


class RaspberryLibcameraSensor(PreviewImageMixin, PeriodicSubprocessStreamRecorder):
    """
    Records a video file using local camera/audio devices plugged to the Raspberry Pi.

    Capture video is stored either as MPEGTS if audio is embedded in it, else as raw H264 stream (without container).

    Records a screenshot before each video clip, if requested (this can be slow).
    """

    sensor_name = "rpi_libcamera"

    @property
    def record_extension(self):
        return ".mpegts" if self._alsa_device_name else ".h264"

    def __init__(
        self,
        alsa_device_name: Optional[str],
        libcameravid_video_parameters: list,
        libcameravid_audio_parameters: list,
        **kwargs
    ):
        super().__init__(**kwargs)
        self._alsa_device_name = alsa_device_name
        self._libcameravid_video_parameters = (libcameravid_video_parameters,)
        self._libcameravid_audio_parameters = (libcameravid_audio_parameters,)

    def _build_subprocess_command_line(self):
        alsa_device_name = self._alsa_device_name

        libcameravid_video_base = [
            "libcamera-vid",
            "--timeout",
            "0",  # NO timeout
            "--nopreview",  # No realtime GUI preview of video
            # Discrepancy, see https://github.com/raspberrypi/libcamera-apps/issues/378#issuecomment-1269461087:
            "--output",
            "pipe:" if alsa_device_name else "-",  # FIXME soon fixed in libcamera-apps, becomes "-o - " instead
            # FIXME ADD DIMENSIONS/COLORS (=MODE) HERE!!!!! See --mode !
        ]

        if self._libcameravid_video_parameters:
            libcameravid_video_parameters = self._libcameravid_video_parameters
        else:
            libcameravid_video_parameters = [
                "--flush",  # Push data ASAP
                "--framerate",
                "30",
                # FOR LATER "--autofocus",  # Only used at startup actually, unless we use "–-keypress" trick
            ]

        libcameravid_audio_base = []
        libcameravid_audio_parameters = []

        if alsa_device_name:

            libcameravid_audio_base = [
                "--codec",
                "libav",
                "--libav-format",
                "mpegts",
                "-q",
                "95",
                "--libav-audio",  # Enabled audio layer
                "--audio-codec",
                "aac",
                "--audio-bitrate",
                "16000",  # LOW bitrate
                # E.g. device: "alsa_input.usb-C-Media_Electronics_Inc._USB_Audio_Device-00.mono-fallback"
                "--audio-device",
                alsa_device_name,
            ]

            if self._libcameravid_audio_parameters:
                libcameravid_audio_parameters = self._libcameravid_audio_parameters
            else:
                libcameravid_audio_parameters = [
                    "--flush",  # Push data ASAP
                    "--framerate",
                    "30",
                    # FOR LATER "--autofocus", but only used at startup actually, unless we use "–-keypress" trick
                ]

        command = (
            libcameravid_video_base
            + libcameravid_video_parameters
            + libcameravid_audio_base
            + libcameravid_audio_parameters
        )
        return command

    def _do_generate_preview_image(self, output, width_px, height_px):
        assert isinstance(output, str), output

        # Launch a subprocess just to capture screenshot
        try:
            snapshot_command_line = [
                "libcamera-jpeg",
                "--nopreview",  # No GUI display
                "--output",
                output,
                "--width",
                str(width_px),
                "--height",
                str(height_px),
                "--immediate",  # No preview phase when taking picture
                # FOR LATER "--autofocus",  # Might be limited by "immediate" mode...
            ]
            logger.info("Taking snapshot with command: %s", " ".join(snapshot_command_line))
            subprocess.check_call(snapshot_command_line, timeout=20)
        except (CalledProcessError, TimeoutExpired) as exc:
            logger.warning("Couldn't generate screenshot in %s sensor: %s", self.sensor_name, exc)


class RaspberryAlsaMicrophoneSensor(ActivityNotificationMixin, PeriodicSubprocessStreamRecorder):
    """
    Records an MP3 audio file using ALSA-compatible microphone (USB or HAT) plugged to the Raspberry Pi.
    """

    sensor_name = "rpi_microphone"
    activity_notification_color = (150, 30, 130)

    subprocess_data_chunk_size = int(0.2 * 1024 ** 2)  # MP3 has smaller size than video

    def __init__(
        self,
        compress_recording: bool,
        arecord_parameters: list,
        arecord_output_format: str,
        ffmpeg_alsa_parameters: list,
        ffmpeg_alsa_output_format: str,
        **kwargs
    ):
        super().__init__(**kwargs)
        self._arecord_parameters = arecord_parameters
        self._arecord_output_format = arecord_output_format
        self._ffmpeg_alsa_parameters = ffmpeg_alsa_parameters
        self._ffmpeg_alsa_output_format = ffmpeg_alsa_output_format
        self._compress_recording = compress_recording

    def _get_actual_ouput_format(self):
        if self._compress_recording:
            return self._ffmpeg_alsa_output_format if self._ffmpeg_alsa_output_format else "mp3"
        else:
            return self._arecord_output_format if self._arecord_output_format else "wav"

    @property
    def record_extension(self):
        return "." + self._get_actual_ouput_format()

    def _build_subprocess_command_line(self):
        if self._compress_recording:

            ffmpeg_alsa_base = ["ffmpeg", "-f", "alsa", "-loglevel", "error"]

            if self._ffmpeg_alsa_parameters:
                ffmpeg_alsa_parameters = self._ffmpeg_alsa_parameters
            else:
                ffmpeg_alsa_parameters = ["-i", "default", "-ac", "1", "-acodec", "libmp3lame", "-ab", "128k"]

            ffmpeg_alsa_final_params = ["-f", self._get_actual_ouput_format(), "pipe:1"]

            command = ffmpeg_alsa_base + ffmpeg_alsa_parameters + ffmpeg_alsa_final_params

        else:

            arecord_base = ["arecord", "-t", self._get_actual_ouput_format()]
            if self._arecord_parameters:
                arecord_parameters = self._arecord_parameters
            else:
                arecord_parameters = [
                    "-c",
                    "1",
                    "-r",
                    "22005",
                    "-f",
                    "S16_LE",
                ]  # If filename is not specified, the standard output is used.

            command = arecord_base + arecord_parameters

        return command


class _CustomPicameraOutputWithEncryptionStream(object):
    """File-like object which pushes data to encryption stream"""

    def __init__(self, encryption_stream: CryptainerEncryptionPipeline):
        self._encryption_stream = encryption_stream

    def write(self, chunk):
        # print("---------> IN EncryptionStreamCustomPicameraOutput write() of %d bytes" % len(chunk))
        with catch_and_log_exception("CustomPicameraOutputWithEncryptionStream.write"):
            self._encryption_stream.encrypt_chunk(chunk)

    def flush(self):
        # print("---------> IN EncryptionStreamCustomPicameraOutput flush()")
        with catch_and_log_exception("CustomPicameraOutputWithEncryptionStream.flush"):
            self._encryption_stream.finalize()


class RaspberryPicameraSensor(
    PreviewImageMixin, ActivityNotificationMixin, PeriodicEncryptionStreamMixin, PeriodicSensorRestarter
):

    sensor_name = "picamera"
    activity_notification_color = (0, 0, 180)

    _picamera = None

    default_parameters = dict(
        # INIT args
        resolution=(1280, 720),
        framerate=30,
        # START args
        format="h264",
        quality=25,
    )

    _current_start_time = None
    _current_buffer = None

    _live_image_preview_pusher = None

    def __init__(self, picamera_parameters: Optional[dict], live_preview_interval_s, local_camera_rotation, **kwargs):
        super().__init__(**kwargs)
        assert isinstance(local_camera_rotation, int), local_camera_rotation
        self._local_camera_rotation = local_camera_rotation
        self._picamera_parameters = picamera_parameters or self.default_parameters

        if live_preview_interval_s:
            self._live_image_preview_pusher = multitimer.MultiTimer(
                interval=live_preview_interval_s, function=self._push_live_preview_image, runonstart=True
            )

    @property
    def record_extension(self):
        return "." + self._picamera_parameters.get("format", "h264")

    def _do_generate_preview_image(self, output, width_px, height_px):
        assert self._picamera  # We generate previews WHILE recording
        assert isinstance(output, str) or hasattr(output, "write"), repr(output)
        self._picamera.capture(output, use_video_port=True, format="jpeg", resize=(width_px, height_px))

    @synchronized
    def _push_live_preview_image(self):
        # print(">>>>>> _push_live_preview_image called")
        with catch_and_log_exception("RaspberryPicameraSensor._push_live_preview_image"):
            assert self.is_running
            output = io.BytesIO()
            self._do_generate_preview_image(output, width_px=480, height_px=480)  # Double the resolution of mini LCD
            output.seek(0)
            notification_image = Image.open(output, formats=["JPEG"])
            self._activity_notification_callback(
                notification_type=ActivityNotificationType.IMAGE_PREVIEW, notification_image=notification_image
            )

    def _create_custom_output(self):
        logger.info("Building new cryptainer encryption stream for Picamera ")
        encryption_stream = self._build_cryptainer_encryption_stream()
        return _CustomPicameraOutputWithEncryptionStream(encryption_stream)

    def _do_start_recording(self):  # pragma: no cover
        self._current_buffer = self._create_custom_output()

        init_parameter_names = ["resolution", "framerate"]
        _picamera_parameters = self._picamera_parameters
        picamera_init_parameters = {k: v for (k, v) in _picamera_parameters.items() if k in init_parameter_names}
        picamera_start_parameters = {k: v for (k, v) in _picamera_parameters.items() if k not in init_parameter_names}

        import picamera  # LAZY loaded

        logger.info("Creating Picamera instance for video and image recording")
        self._picamera = picamera.PiCamera(**picamera_init_parameters)
        self._picamera.rotation = self._local_camera_rotation
        self._picamera.start_recording(self._current_buffer, **picamera_start_parameters)
        self._conditionally_regenerate_preview_image()
        if self._live_image_preview_pusher:
            self._live_image_preview_pusher.start()

    def _do_stop_recording(self):  # pragma: no cover

        logger.info("Destroying Picamera instance")
        if self._live_image_preview_pusher:
            self._live_image_preview_pusher.stop()
        self._picamera.stop_recording()
        self._picamera.close()  # IMPORTANT
        self._picamera = None

    def _do_restart_recording(self):
        new_buffer = self._create_custom_output()
        self._picamera.split_recording(new_buffer)
        self._current_buffer = new_buffer
