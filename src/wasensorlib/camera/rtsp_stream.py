import logging
import subprocess
import threading

from datetime import timezone, datetime

from wacryptolib.sensor import TarfileRecordsAggregator
from wacryptolib.utilities import PeriodicTaskHandler, synchronized


logger = logging.getLogger(__name__)


def get_utc_now_date():  # FIXME remove this
    """Return current datetime with UTC timezone."""
    return datetime.now(tz=timezone.utc)


class PeriodicStreamPusher(PeriodicTaskHandler):
    """
    This class launches an external sensor, and periodically pushes thecollected data
    to a tarfile aggregator.
    """

    _current_start_time = None

    # Fields to be overridden
    sensor_name = None
    record_extension = None

    def __init__(self,
                 interval_s: float,
                 tarfile_aggregator: TarfileRecordsAggregator):
        super().__init__(interval_s=interval_s, runonstart=False)
        self._tarfile_aggregator = tarfile_aggregator
        assert self.sensor_name, self.sensor_name
        assert not hasattr(self, "_lock")
        self._lock = threading.Lock()

    @synchronized
    def start(self):
        """
        FR : Methode qui permet de ne pas redémarrer une deuxième fois l'enregistrement'

        """
        super().start()

        logger.info(">>> Starting sensor %s" % self)

        self._current_start_time = get_utc_now_date()

        self._do_start_recording()

        logger.info(">>> Starting sensor %s" % self)

    def _do_start_recording(self):
        raise NotImplementedError("%s -> _do_start_recording" % self.sensor_name)

    @synchronized
    def stop(self):
        super().stop()

        logger.info(">>> Starting sensor %s" % self)

        from_datetime = self._current_start_time
        to_datetime = get_utc_now_date()

        data = self._do_stop_recording()

        self._do_push_buffer_file_to_aggregator(data=data, from_datetime=from_datetime, to_datetime=to_datetime)

        logger.info(">>> Starting sensor %s" % self)

    def _do_stop_recording(self):
        raise NotImplementedError("%s -> _do_stop_recording" % self.sensor_name)

    def _do_push_buffer_file_to_aggregator(self, data, from_datetime, to_datetime):

        fn = "abcde_%s.ismv" % from_datetime.strftime("%H%M%S")

        ''' TEMP
        print("WRITING FILE", fn)
        with open(fn, "wb") as f:
            f.write(data)
        '''

        assert from_datetime and to_datetime, (from_datetime, to_datetime)

        self._tarfile_aggregator.add_record(
            sensor_name=self.sensor_name,
            from_datetime=from_datetime,
            to_datetime=to_datetime,
            extension=self.record_extension,
            data=data,
        )

    @synchronized
    def _offloaded_run_task(self):

        if not self.is_running:
            return

        from_datetime = self._current_start_time
        to_datetime = datetime.now(tz=timezone.utc)

        data = self._do_stop_recording() # Renames target files

        self._current_start_time = get_utc_now_date()  # RESET
        self._do_start_recording()  # Must be restarded imediately

        if data:
            self._do_push_buffer_file_to_aggregator(data=data, from_datetime=from_datetime, to_datetime=to_datetime)


class RtspCameraSensor(PeriodicStreamPusher):  # FIXME rename all and normalize

    sensor_name = "rtsp_camera"
    record_extension = ".mp4"

    def __init__(self,
                 interval_s,
                 tarfile_aggregator,
                 video_stream_url):
        super().__init__(interval_s=interval_s, tarfile_aggregator=tarfile_aggregator)

        self._video_stream_url = video_stream_url

    def _launch_and_wait_ffmpeg_process(self):

        exec = [
            "ffmpeg",
            "-y",  # Always say yes to questions
            "-rtsp_transport", "tcp"
        ]
        input = [
            "-i",
            self._video_stream_url
        ]
        codec = [
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
            "warning"
        ]
        output = [
            "pipe:1"  # Pipe to stdout
        ]

        pipeline = exec + input + codec + logs + output

        logger.info("Calling RtspCameraSensor subprocess command: {}".format(" ".join(pipeline)))
        self._subprocess = subprocess.Popen(pipeline,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=None)  # Stderr is left floating for now

        self._stdout_buff = []
        self._stdout_thread = threading.Thread(target=self._subprocess._readerthread,
                                                args=(self._subprocess.stdout, self._stdout_buff))
        self._stdout_thread.start()

        #returncode = self.process.wait()
        #if returncode:
        #    logger.warning("recorder process exited with abnormal code %s", returncode)

    def _do_start_recording(self):
        self._launch_and_wait_ffmpeg_process()

    def _do_stop_recording(self):
        self._subprocess.stdin.write(b"q")  # FFMPEG command to quit
        self._subprocess.stdin.close()
        self._stdout_thread.join(timeout=10)
        buffer = self._stdout_buff[0] if self._stdout_buff else b""
        return buffer

    @staticmethod
    def __BROKEN_extract_preview_image(buffer):  #FIXME -seems broken, only for jpeg stream
        #stream = urllib.request.urlopen('http://192.168.0.51/video.cgi?resolution=1920x1080')
        a = buffer.find(b'\xff\xd8')
        b = buffer.find(b'\xff\xd9')
        if a != -1 and b != -1 and b > a:
            jpg = buffer[a:b+2]
            filename = 'capture.jpeg'
            import cv2, np
            i = cv2.imdecode(np.fromstring(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
            cv2.imwrite(filename, i)
            return filename
        else:
            print(">>>>>>>>", a, b, buffer)
            logger.warning("Couldn't find a preview frame in RTSP buffer of length %s" % len(buffer))

        """ SEE:
        command = ["ffmpeg", "-i", str(path), "-r", "1", "-vframes", "1", str(preview_image_path), "-y"]  # "-f",  str(preview_image_path.parent) To rescale: -s WxH
        logger.info("Calling preview extraction command: %s", str(command))
        try:
            res = subprocess.run(command, timeout=10)  # Process is killed brutally if timeout
            logger.info("Preview extraction command exited with code %s", res.returncode)
        except subprocess.TimeoutExpired:
            logger.warning("Preview extraction failed with timeout")
            """