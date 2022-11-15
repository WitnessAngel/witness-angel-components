
import logging
from datetime import timezone, datetime
import re
import subprocess
from pathlib import Path
from wacomponents.i18n import tr
from kivy.logger import Logger as logger

from wacomponents.sensors.camera._camera_base import PreviewImageMixin, ActivityNotificationMixin
from wacryptolib.sensor import PeriodicSubprocessStreamRecorder

logger = logging.getLogger(__name__)


def get_utc_now_date():  # FIXME remove this
    """Return current datetime with UTC timezone."""
    return datetime.now(tz=timezone.utc)


def get_ffmpeg_version() -> tuple:
    """Returns a pair with version as a float(or None), along with an error message (or None if success)."""
    try:
        output = subprocess.check_output(["ffmpeg", "-version"], stderr=subprocess.STDOUT)
    except OSError:
        logger.warning("Error while calling ffmpeg", exc_info=True)
        return None, tr.f(tr._("Ffmpeg module not found, please ensure it is in your PATH"))

    output = output.decode("ascii", "ignore").lower()

    regex = r'ffmpeg version .?(\d\.\d)'  # E.g. FFMPEG SNAPs contain a "n" before version number
    match = re.search(regex, output)

    if match is None:
        return None, tr.f(tr._("Ffmpeg module is installed, but beware its version couldn't be determined"))

    ffmpeg_version = match.group(1)
    return float(ffmpeg_version), None


class RtspCameraSensor(PreviewImageMixin, ActivityNotificationMixin, PeriodicSubprocessStreamRecorder):
    """
    Records an RTSP stream, by default WITHOUT AUDIO (unless ffmpeg_rtsp_parameters override that=.

    Automatically extracts a screenshot at the beginning of each recording.
    """

    sensor_name = "rtsp_camera"
    activity_notification_color = (0, 150, 0)

    def __init__(self,
                 video_stream_url: str,
                 ffmpeg_rtsp_parameters: list,
                 ffmpeg_rtsp_output_format: str,
                 **kwargs):
        super().__init__(**kwargs)
        assert video_stream_url, video_stream_url
        self._video_stream_url = video_stream_url
        self._ffmpeg_rtsp_parameters = ffmpeg_rtsp_parameters
        self._ffmpeg_rtsp_output_format = ffmpeg_rtsp_output_format

    def _get_actual_ouput_format(self):
        return self._ffmpeg_rtsp_output_format if self._ffmpeg_rtsp_output_format else "mp4"

    @property
    def record_extension(self):
        return "." + self._get_actual_ouput_format()

    def _build_subprocess_command_line(self):
        ffmpeg_version, _error_msg = get_ffmpeg_version()

        additional_input_args = []
        timeout_microseconds = "5000000"
        if ffmpeg_version is not None:
            # Force failure if input can't be joined anymore (microseconds!)
            if ffmpeg_version >= 5:
                # This previously meant "listen timeout"
                additional_input_args = ["-timeout", timeout_microseconds]
            else:
                additional_input_args = ["-stimeout", timeout_microseconds]

        executable = [
            "ffmpeg",
            "-y",  # Always say yes to questions
            "-hide_banner",  # Hide useless "library configuration mismatch" stuffs
        ]

        input = additional_input_args + [
            "-rtsp_flags", "prefer_tcp",  # Safer alternative to ( "-rtsp_transport", "tcp", )
            "-fflags", "+igndts",  # Fix "non-monotonous DTS in output stream" error
            # Beware these flags only concern HTTP, no use for them in RTPS!
            #  "-reconnect", "1", "-reconnect_at_eof", "1", "-reconnect_streamed", "1",
            #  "-reconnect_delay_max", "10",  "-reconnect_on_network_error", "1",
            "-i",
            self._video_stream_url,
        ]

        if self._ffmpeg_rtsp_parameters:
            codec = self._ffmpeg_rtsp_parameters
        else:
            codec = [
                #"-copytb", "1", (doesn't work for timestamps)
                "-vcodec", "copy",
                "-an",  # NO AUDIO FOR NOW, codec pcm-mulaw not supported for Bluestork cameras...
                # "-acodec", "copy",
                "-map", "0",
                "-f", "ismv",  # https://ffmpeg.org/ffmpeg-formats.html#mov_002c-mp4_002c-ismv necessary for non-seekable output
                "-movflags", "empty_moov+delay_moov",  # empty_moov is already implicit for ISMV, delay_moov is for "Non-monotonous DTS in output stream"
                "-probesize", "128",
                "-analyzeduration", "500",
            ]

        logs = [
            "-loglevel",
            "info"  # Values: error, warning, info, debug or trace
        ]
        video_output = [
            "-f", self._get_actual_ouput_format(),
            "pipe:1",  # Pipe to stdout
            #"-vf", "fps=1/60", "img%03d.jpg"
        ]

        preview_image_output = []
        if self._preview_image_path:
            preview_image_output = [
                "-frames:v",  "1",
                "-filter:v", "scale=%d:-1,hue=s=0" % self.PREVIEW_IMAGE_WIDTH_PX,  # Keep image ratio!
                str(self._preview_image_path),
            ]
        subprocess_command_line = executable + input + codec + logs + video_output + preview_image_output
        return subprocess_command_line
