import logging
import subprocess
from pathlib import Path
from subprocess import CalledProcessError, TimeoutExpired
from typing import Optional

from wacryptolib.sensor import PeriodicSubprocessStreamRecorder


logger = logging.getLogger(__name__)


def list_pulseaudio_microphone_names():
    """Equivalent to command:  pactl list | grep -A2 'Source #' | grep 'Name:' 
    """
    import pulsectl
    pulse = pulsectl.Pulse('witness-angel-device')
    results = pulse.source_list()
    source_names = [res.name for res in results]
    # We ignore "sink monitors" (e.g. HDMI output monitor) useless for us
    microphone_names = [name for name in source_names if "input" in name.lower()]
    #print(">>>>>>>>PULSECTL microphone_names IS", microphone_names)
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
            "--framerate", "30",
            # FOR LATER "--autofocus",  # Only used at startup actually, unless we use "–-keypress" trick
            # Discrepancy, see https://github.com/raspberrypi/libcamera-apps/issues/378#issuecomment-1269461087:
            "--output", "pipe:" if alsa_device_name else "-",
            #FIXME ADD DIMENSIONS/COLORS (=MODE) HERE!!!!!
        ]

        if alsa_device_name:
            libcamera_command_line += [
                "--codec", "libav",
                "--libav-format", "mpegts",
                "-q", "95",
                "--libav-audio",   # Enabled audio layer
                "--audio-codec", "aac",
                "--audio-bitrate", "16000",  # LOW bitrate
                # E.g. device: "alsa_input.usb-C-Media_Electronics_Inc._USB_Audio_Device-00.mono-fallback"
                "--audio-device", alsa_device_name,
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
                snapshot_width_px = 140
                snapshot_height_px = 104  # Even number for 4/3 format
                snapshot_command_line = [
                                    "libcamera-jpeg",
                                    "--nopreview",  # No GUI display
                                    "--output", str(self._preview_image_path),
                                    "--width", str(snapshot_width_px),
                                    "--height", str(snapshot_height_px),
                                    "--immediate",  # No preview phase when taking picture
                                    # FOR LATER "--autofocus",  # Might be limited by "immediate" mode...
                                ]
                logger.info("Taking camera snapshot with command: %s", " ".join(snapshot_command_line))
                subprocess.check_call(snapshot_command_line, timeout=20)
            except (CalledProcessError, TimeoutExpired) as exc:
                logger.warning("Couldn't get screenshot in %s sensor: %s", self.sensor_name, exc)

        return super()._launch_and_consume_subprocess( *args, **kwargs)


class RaspberryAlsaMicrophoneSensor(PeriodicSubprocessStreamRecorder):
    """
    Records an MP3 audio file using ALSA-compatible microphone (USB or HAT) plugged to the Raspberry Pi.
    """

    sensor_name = "rpi_microphone"
    record_extension = ".mp3"

    subprocess_data_chunk_size = int(0.2 * 1024**2)  # MP3 has smaller size than video

    def __init__(self,
                 compress_recording: bool = False,
                 **kwargs):
        super().__init__(**kwargs)
        self._compress_recording = compress_recording

    @property
    def record_extension(self):
        return ".mp3" if self._compress_recording else ".wav"

    def _build_subprocess_command_line(self):
        if self._compress_recording:

            command = [
                "ffmpeg",
                "-f", "alsa",
                "-ac", "1",  # TODO make it selectable for 2-mic sources?
                "-i", "default",  # TODO allow selection of source, later?
                "-acodec", "libmp3lame",
                "-ab", "128k",
                "-f", "mp3",
                "-loglevel", "error",
                "pipe:1"
            ]

        else:

            command = [
                "arecord",
                "-c", "1",
                "-r", "22005",
                "-f", "S16_LE",
                "-t", "wav"
            ]  # If filename is not specified, the standard output is used.

        return command

