import logging
import subprocess
from subprocess import CalledProcessError, TimeoutExpired
from typing import Optional

import picamera
from wacomponents.sensors.camera._camera_base import PreviewImageMixin, ActivityNotificationMixin
from wacryptolib.cryptainer import CryptainerEncryptionPipeline
from wacryptolib.sensor import PeriodicSubprocessStreamRecorder, PeriodicEncryptionStreamMixin, PeriodicSensorRestarter

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


def is_legacy_rpi_camera_enabled():
    try:
        output = subprocess.check_output(["vcgencmd", "get_camera"], text=True)
        return ("supported=1 " in output)
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

    def __init__(self,
                 raspivid_parameters: list,
                 **kwargs):
        super().__init__(**kwargs)
        self._raspivid_parameters = raspivid_parameters

    def _generate_preview_image(self, output_path, width_px, height_px):

        try:
            snapshot_command_line = [
                "raspistill",
                "--nopreview",  # No GUI display
                "--output", str(self._preview_image_path),
                "--width", str(width_px),
                "--height", str(height_px),
                "--quality", "90",
                "-v",
            ]
            logger.info("Taking camera legacy snapshot with command: %s", " ".join(snapshot_command_line))  # Fixme deduplicate this
            subprocess.check_call(snapshot_command_line, timeout=20)
        except (CalledProcessError, TimeoutExpired) as exc:
            logger.warning("Couldn't generate legacy screenshot in %s sensor: %s", self.sensor_name, exc)

    def _build_subprocess_command_line(self):

        raspivid_command_line_base = [
           "raspivid",
            "--timeout", "0",  # NO timeout
            "--nopreview",
            "-v",
        ]

        if self._raspivid_parameters:
            raspivid_parameters = self._raspivid_parameters
        else:
            raspivid_parameters = [
                "--framerate", "30",
                "-pf", "baseline",  # H264 profile tweaking, lots of other options exist
                # Set most common medium mode for V1 (OV5647) and V2 (IMX219) cameras
                # See https://www.waveshare.com/wiki/RPi_Camera
                "--width", "1296",
                "--height", "730",
                "--output", "-",
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

    def __init__(self,
                 alsa_device_name: Optional[str],
                 libcameravid_video_parameters: list,
                 libcameravid_audio_parameters: list,
                 **kwargs):
        super().__init__(**kwargs)
        self._alsa_device_name = alsa_device_name
        self._libcameravid_video_parameters = libcameravid_video_parameters,
        self._libcameravid_audio_parameters = libcameravid_audio_parameters,

    def _build_subprocess_command_line(self):
        alsa_device_name = self._alsa_device_name

        libcameravid_video_base = [
           "libcamera-vid",
            "--timeout", "0",  # NO timeout
            "--nopreview",  # No realtime GUI preview of video
            # Discrepancy, see https://github.com/raspberrypi/libcamera-apps/issues/378#issuecomment-1269461087:
            "--output", "pipe:" if alsa_device_name else "-",  # FIXME soon fixed in libcamera-apps, becomes "-o - " instead
            #FIXME ADD DIMENSIONS/COLORS (=MODE) HERE!!!!! See --mode !
        ]

        if self._libcameravid_video_parameters:
            libcameravid_video_parameters = self._libcameravid_video_parameters
        else:
            libcameravid_video_parameters = [
                "--flush",  # Push data ASAP
                "--framerate", "30",
                # FOR LATER "--autofocus",  # Only used at startup actually, unless we use "–-keypress" trick
            ]

        libcameravid_audio_base = []
        libcameravid_audio_parameters = []

        if alsa_device_name:

            libcameravid_audio_base = [
                "--codec", "libav",
                "--libav-format", "mpegts",
                "-q", "95",
                "--libav-audio",   # Enabled audio layer
                "--audio-codec", "aac",
                "--audio-bitrate", "16000",  # LOW bitrate
                # E.g. device: "alsa_input.usb-C-Media_Electronics_Inc._USB_Audio_Device-00.mono-fallback"
                "--audio-device", alsa_device_name,
            ]

            if self._libcameravid_audio_parameters:
                libcameravid_audio_parameters = self._libcameravid_audio_parameters
            else:
                libcameravid_audio_parameters = [
                    "--flush",  # Push data ASAP
                    "--framerate", "30",
                    # FOR LATER "--autofocus", but only used at startup actually, unless we use "–-keypress" trick
                ]

        command = libcameravid_video_base + libcameravid_video_parameters + libcameravid_audio_base + libcameravid_audio_parameters
        return command

    def _generate_preview_image(self, output_path, width_px, height_px):

        # Launch a subprocess just to capture screenshot
        try:
            snapshot_command_line = [
                                "libcamera-jpeg",
                                "--nopreview",  # No GUI display
                                "--output", str(self._preview_image_path),
                                "--width", str(width_px),
                                "--height", str(height_px),
                                "--immediate",  # No preview phase when taking picture
                                # FOR LATER "--autofocus",  # Might be limited by "immediate" mode...
                            ]
            logger.info("Taking camera snapshot with command: %s", " ".join(snapshot_command_line))
            subprocess.check_call(snapshot_command_line, timeout=20)
        except (CalledProcessError, TimeoutExpired) as exc:
            logger.warning("Couldn't get screenshot in %s sensor: %s", self.sensor_name, exc)


class RaspberryAlsaMicrophoneSensor(ActivityNotificationMixin, PeriodicSubprocessStreamRecorder):
    """
    Records an MP3 audio file using ALSA-compatible microphone (USB or HAT) plugged to the Raspberry Pi.
    """

    sensor_name = "rpi_microphone"
    activity_notification_color = (150, 30, 130)

    subprocess_data_chunk_size = int(0.2 * 1024**2)  # MP3 has smaller size than video

    def __init__(self,
                 compress_recording: bool,
                 arecord_parameters: list,
                 arecord_output_format: str,
                 ffmpeg_alsa_parameters: list,
                 ffmpeg_alsa_output_format: str,
                 **kwargs):
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

            ffmpeg_alsa_base = [
                "ffmpeg",
                "-f", "alsa",
                "-loglevel", "error",
            ]

            if self._ffmpeg_alsa_parameters:
                ffmpeg_alsa_parameters = self._ffmpeg_alsa_parameters
            else:
                ffmpeg_alsa_parameters = [
                    "-i", "default",
                    "-ac", "1",
                    "-acodec", "libmp3lame",
                    "-ab", "128k",
                ]

            ffmpeg_alsa_final_params = ["-f", self._get_actual_ouput_format(), "pipe:1"]

            command = ffmpeg_alsa_base + ffmpeg_alsa_parameters + ffmpeg_alsa_final_params

        else:

            arecord_base = [
                "arecord",
                "-t", self._get_actual_ouput_format(),
            ]
            if self._arecord_parameters:
                arecord_parameters = self._arecord_parameters
            else:
                arecord_parameters = [
                    "-c", "1",
                    "-r", "22005",
                    "-f", "S16_LE",
                ]  # If filename is not specified, the standard output is used.

            command = arecord_base + arecord_parameters

        return command


class CustomPicameraOutputWithEncryptionStream(object):
    """File-like object which pushes data to encryption stream"""
    def __init__(self, encryption_stream: CryptainerEncryptionPipeline):
        self._encryption_stream = encryption_stream

    def write(self, chunk):
        print("---------> IN EncryptionStreamCustomPicameraOutput write() of %d bytes" % len(chunk))
        try:
            self._encryption_stream.encrypt_chunk(chunk)
        except Exception as exc:
            print("<>>>>>>>>>>>>>>>>>>>>>>>1", exc)

    def flush(self):
        print("---------> IN EncryptionStreamCustomPicameraOutput flush()")
        try:
            self._encryption_stream.finalize()
        except Exception as exc:
            print("<>>>>>>>>>>>>>>>>>>>>>>>2", exc)


class RaspberryPicameraSensor(PeriodicEncryptionStreamMixin, PeriodicSensorRestarter):

    sensor_name = "picamera"
    record_extension = ".h264"

    _picamera = None

    _resolution = (1280, 720)
    _framerate = 30

    _current_start_time = None

    def _create_custom_output(self):
        encryption_stream = self._build_cryptainer_encryption_stream()
        return CustomPicameraOutputWithEncryptionStream(encryption_stream)

    def _do_start_recording(self):  # pragma: no cover
        print("starting picamera")
        self._current_buffer = self._create_custom_output()
        self._picamera = picamera.PiCamera(resolution=self._resolution, framerate=self._framerate)
        self._picamera.start_recording(self._current_buffer, format='h264', quality=25)

    def _do_stop_recording(self):  # pragma: no cover
        print("stopping picamera")
        self._picamera.stop_recording()
        self._picamera.close()  # IMPORTANT
        self._picamera = None
        return None
        #self._current_buffer.seek(0)
        #final_recording_bytes = self._current_buffer.read()
        #self._current_buffer = None
        #return final_recording_bytes

    # LET IT NOT IMPLEMENTED def _handle_post_stop_data(self, payload, from_datetime, to_datetime):
    #    assert isinstance(payload, bytes)  # Might be empty bytes though

    def _do_restart_recording(self):

        #new_buffer = io.BytesIO()
        new_buffer = self._create_custom_output()
        self._picamera.split_recording(new_buffer)
        ###assert self._current_buffer._encryption_pipeline
        self._current_buffer = new_buffer

        #self._current_buffer.seek(0)
        #previous_recording_bytes = self._current_buffer.read()
        #return previous_recording_bytes
