
import logging
import threading
from datetime import timezone, datetime
import re
import subprocess
from pathlib import Path
from wacomponents.i18n import tr
from kivy.logger import Logger as logger

from wacryptolib.cryptainer import CRYPTAINER_DATETIME_FORMAT
from wacryptolib.sensor import PeriodicSubprocessStreamRecorder
from wacryptolib.utilities import PeriodicTaskHandler, synchronized

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


class RtspCameraSensor(PeriodicSubprocessStreamRecorder):  # FIXME rename all and normalize

    sensor_name = "rtsp_camera"
    record_extension = ".mp4"

    _subprocess = None

    def __init__(self,
                 interval_s,
                 cryptainer_storage,
                 video_stream_url: str,
                 preview_image_path: Path):
        super().__init__(interval_s=interval_s, cryptainer_storage=cryptainer_storage)
        assert video_stream_url and preview_image_path, (video_stream_url, preview_image_path)
        self._video_stream_url = video_stream_url
        self._preview_image_path = preview_image_path

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
            "info"  # Else, info, debug or trace
        ]
        video_output = [
            "pipe:1",  # Pipe to stdout

            #"-vf", "fps=1/60", "img%03d.jpg"
        ]
        preview_image_output = [
            "-frames:v",  "1", "-filter:v", "scale=140:-1,hue=s=0", str(self._preview_image_path),  # FIXME parametrize DIMENSIONS
        ]
        subprocess_command_line = executable + input + codec + logs + video_output + preview_image_output
        return subprocess_command_line

    def _launch_and_consume_subprocess(self, *args, **kwargs):

        # Cleanup dangling preview image
        try:
            self._preview_image_path.unlink()  # FIXME use "missing_ok" soon
        except FileNotFoundError:
            pass

        return super()._launch_and_consume_subprocess( *args, **kwargs)
