import logging
import subprocess
from pathlib import Path
from subprocess import CalledProcessError, TimeoutExpired
from typing import Optional

from wacryptolib.sensor import PeriodicSubprocessStreamRecorder


logger = logging.getLogger(__name__)


def list_pulseaudio_microphone_names():
    import pulsectl
    pulse = pulsectl.Pulse('witness-angel-device')
    results = pulse.source_list()
    source_names = [res.name for res in results]
    # We ignore "sink monitors" (e.g. HDMI output monitor) useless for us
    microphone_names = [name for name in source_names if "input" in name.lower()]
    print(">>>>>>>>PULSECTL microphone_names IS", microphone_names)
    return microphone_names


class RaspberryLibcameraSensor(PeriodicSubprocessStreamRecorder):
    """
    Records a video file using local camera/audio devices plugged to the Raspberry Pi.

    Capture video is stored either as MPEGTS if audio is embedded in it, else as raw H264 stream (without container).

    Records a screenshot BETWEEN each video recording, if requested (this can be slow).
    """

    sensor_name = "rpi_camera"

    @property
    def record_extension(self):
        return ".mpegts" if self._alsa_device_name else ".h264"

    def __init__(self,
                 preview_image_path: Optional[str] = None,
                 alsa_device_name: Optional[str]= None,
                 **kwargs):
        super().__init__(**kwargs)
        self._preview_image_path = preview_image_path
        self._alsa_device_name = alsa_device_name

    def _build_subprocess_command_line(self):
        alsa_device_name = self._alsa_device_name

        libcamera_command_line = [
           "libcamera-vid",
            "--timeout", "0",  # NO timeout
            "--nopreview",  # No realtime GUI preview of video
            "--flush",  # Push data ASAP
            # Discrepancy, see https://github.com/raspberrypi/libcamera-apps/issues/378#issuecomment-1269461087:
            "--output", "pipe:" if alsa_device_name else "-",
            #FIXME ADD DIMENSIOSN AND FPS HERE!!!!!
        ]

        if alsa_device_name:
            libcamera_command_line += [
                "--codec", "libav",
                "--libav-format", "mpegts",
                "--libav-audio",   # Enabled audio layer
                "--audio-codec", "aac",
                "--audio-bitrate", "16384",  # LOW bitrate
                "--audio-device", alsa_device_name,  # E.g. "alsa_input.usb-C-Media_Electronics_Inc._USB_Audio_Device-00.mono-fallback"
            ]

        return libcamera_command_line

    def _launch_and_consume_subprocess(self, *args, **kwargs):

        if self._preview_image_path:

            # Cleanup dangling preview image
            try:
                self._preview_image_path.unlink()  # FIXME use "missing_ok" soon
            except FileNotFoundError:
                pass

            # SPECIAL STEP - launch a subprocess just to capture screenshot
            try:
                screenshot_width_px = 140
                screenshot_height_px = int(screenshot_width_px / (4/3))
                subprocess.check_call([
                    "libcamera-jpeg",
                    "--nopreview",  # No GUI display
                    "--output", self._preview_image_path,
                    "--width", str(screenshot_width_px),
                    "--height", str(screenshot_height_px),
                    "--immediate",  # No preview phase when taking picture
                ],
                timeout=5)
            except (CalledProcessError, TimeoutExpired) as exc:
                logger.warning("Couldn't get screenshot in %s sensor: %s", self.sensor_name, exc)

        return super()._launch_and_consume_subprocess( *args, **kwargs)


class RaspberryAlsaMicrophoneSensor(PeriodicSubprocessStreamRecorder):
    """
    Records an MP3 audio file using ALSA-compatible microphone (USB or HAT) plugged to the Raspberry Pi.
    """

    sensor_name = "rpi_microphone"
    record_extension = ".mp3"

    def _build_subprocess_command_line(self):
        return [
            "ffmpeg",
            "-f", "alsa",
            "-ac", "1",  # TODO make it selectable for 2-mic sources?
            "-i", "default",  # TODO allow selection of source, later?
            "-acodec", "libmp3lame",
            "-ab", "128k",
            "-f", "mp3",
            "pipe:1"
        ]

