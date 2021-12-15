import io
import logging
import subprocess
import threading

from datetime import timezone, datetime
from pathlib import Path

from wacryptolib.container import CONTAINER_DATETIME_FORMAT
from wacryptolib.sensor import TarfileRecordsAggregator
from wacryptolib.utilities import PeriodicTaskHandler, synchronized


logger = logging.getLogger(__name__)


DATA_CHUNK_SIZE =  1024**2
SUPROCESS_BUFFER_SIZE = DATA_CHUNK_SIZE * 5


def get_utc_now_date():  # FIXME remove this
    """Return current datetime with UTC timezone."""
    return datetime.now(tz=timezone.utc)

'''
# FIXME move this to wacryptolib!
class PeriodicStreamPusher__old(PeriodicTaskHandler):
    """
    This class launches an external sensor, and periodically pushes the collected data
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

        logger.info(">>> Started sensor %s" % self)

    def _do_start_recording(self):
        raise NotImplementedError("%s -> _do_start_recording" % self.sensor_name)

    @synchronized
    def stop(self):
        super().stop()

        logger.info(">>> Stopping sensor %s" % self)

        from_datetime = self._current_start_time
        to_datetime = get_utc_now_date()

        data = self._do_stop_recording()

        self._do_push_buffer_file_to_aggregator(data=data, from_datetime=from_datetime, to_datetime=to_datetime)

        logger.info(">>> Stopped sensor %s" % self)

    def _do_stop_recording(self):
        raise NotImplementedError("%s -> _do_stop_recording" % self.sensor_name)

    def _do_push_buffer_file_to_aggregator(self, data, from_datetime, to_datetime):

        fn = "abcde_%s.ismv" % from_datetime.strftime("%H%M%S")


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

'''







# FIXME move this to wacryptolib!
class PeriodicStreamPusher(PeriodicTaskHandler):

    _current_start_time = None

    # Fields to be overridden
    sensor_name = None
    record_extension = None

    def __init__(self,
                 interval_s: float,):
        super().__init__(interval_s=interval_s, runonstart=False)
        assert self.sensor_name, self.sensor_name
        assert not hasattr(self, "_lock")
        self._lock = threading.Lock()

    def _build_filename_base(self, from_datetime):
        extension = self.record_extension
        assert extension.startswith("."), extension
        from_ts = from_datetime.strftime(CONTAINER_DATETIME_FORMAT)
        filename = "{from_ts}_container{extension}".format(**locals())
        assert " " not in filename, repr(filename)
        return filename

    @synchronized
    def start(self):
        """
        FR : Methode qui permet de ne pas redémarrer une deuxième fois l'enregistrement'
        """
        super().start()

        logger.info(">>> Starting sensor %s" % self)

        self._current_start_time = get_utc_now_date()

        self._do_start_recording()

        logger.info(">>> Started sensor %s" % self)

    def _do_start_recording(self):
        raise NotImplementedError("%s -> _do_start_recording" % self.sensor_name)

    @synchronized
    def stop(self):
        super().stop()

        logger.info(">>> Stopping sensor %s" % self)

        from_datetime = self._current_start_time
        to_datetime = get_utc_now_date()

        data = self._do_stop_recording()

        if data is not None:
            self._handle_post_stop_data(data=data, from_datetime=from_datetime, to_datetime=to_datetime)

        logger.info(">>> Stopped sensor %s" % self)

    def _do_stop_recording(self):
        raise NotImplementedError("%s -> _do_stop_recording" % self.sensor_name)

    def _handle_post_stop_data(self, data, from_datetime, to_datetime):
        raise NotImplementedError("%s -> _handle_post_stop_data" % self.sensor_name)

    @synchronized
    def _offloaded_run_task(self):

        if not self.is_running:
            return

        from_datetime = self._current_start_time
        to_datetime = datetime.now(tz=timezone.utc)

        data = self._do_stop_recording() # Renames target files

        self._current_start_time = get_utc_now_date()  # RESET
        self._do_start_recording()  # Must be restarded imediately

        if data is not None:
            self._handle_post_stop_data(data=data, from_datetime=from_datetime, to_datetime=to_datetime)





class RtspCameraSensor(PeriodicStreamPusher):  # FIXME rename all and normalize

    sensor_name = "rtsp_camera"
    record_extension = ".mp4"

    _subprocess = None

    def __init__(self,
                 interval_s,
                 container_storage,
                 video_stream_url: str,
                 preview_image_path: Path):
        super().__init__(interval_s=interval_s)
        assert video_stream_url and preview_image_path, (video_stream_url, preview_image_path)
        self._container_storage = container_storage
        self._container_encryption_stream = None
        self._video_stream_url = video_stream_url
        self._preview_image_path = preview_image_path

    def _launch_and_wait_ffmpeg_process(self):

        exec = [
            "ffmpeg",
            "-y",  # Always say yes to questions

        ]
        input = [
            "-rtsp_flags", "prefer_tcp",  # Safer alternative to ( "-rtsp_transport", "tcp", )
            "-timeout", "5000",  # Force failure if input can't be joined anymore
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
        pipeline = exec + input + codec + logs + video_output + preview_image_output

        # Cleanup dangling preview image
        try:
            self._preview_image_path.unlink()  # FIXME use "missing_ok" soon
        except FileNotFoundError:
            pass

        logger.warning("Calling RtspCameraSensor subprocess command: {}".format(" ".join(pipeline)))
        self._subprocess = subprocess.Popen(
            pipeline,
            bufsize=SUPROCESS_BUFFER_SIZE,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)  # Stderr is left floating for now

        def _stdoutreaderthread(fh):
            # Backported from Popen._readerthread of Python3.8
            while True:
                chunk = fh.read(DATA_CHUNK_SIZE)
                assert chunk is not None  # We're NOT in non-blocking mode!
                if chunk:
                    print(">>>>>>>>>> ENCRYPTING CHUNK OF LENGTH", len(chunk))
                    self._container_encryption_stream.encrypt_chunk(chunk)
                else:
                    break
            print(">>>>>>>>>> FINALIZING CONTAINER ENCRYPTION STREAM")
            self._container_encryption_stream.finalize()
            fh.close()

        self._stdout_thread = threading.Thread(target=_stdoutreaderthread,
                                                args=(self._subprocess.stdout,))
        self._stdout_thread.start()

        def _sytderrreaderthread(fh):
            for line in fh:
                ##print(b">>>>", repr(line).encode("ascii"))
                line_str = repr(line)  #  line.decode("ascii", "ignore")
                logger.warning("SUBPROCESS: %s" % line_str.rstrip("\n"))
            fh.close()
        self._stderr_thread = threading.Thread(target=_sytderrreaderthread,
                                                args=(self._subprocess.stderr,))
        self._stderr_thread.start()

        #returncode = self.process.wait()
        #if returncode:
        #    logger.warning("recorder process exited with abnormal code %s", returncode)

    def _do_start_recording(self):
        self._container_encryption_stream = self._container_storage.create_container_encryption_stream(
            self._build_filename_base(self._current_start_time), metadata=None, dump_initial_container=True)
        self._launch_and_wait_ffmpeg_process()

    def _do_stop_recording(self):
        if self._subprocess is None:
            logger.warning("No subprocess to be terminated in RtspCameraSensor stop-recording")
            return  # Init failed previously
        retcode = self._subprocess.poll()
        if retcode is not None:
            logger.warning("Subprocess already terminated with code %s in RtspCameraSensor stop-recording" % retcode)
            return  # Stream must have crashed
        try:
            self._subprocess.stdin.write(b"q")  # FFMPEG command to quit
            self._subprocess.stdin.close()
            self._stdout_thread.join(timeout=10)
        except Exception as exc:
            logger.warning("Failed normal termination of ffmpeg subprocess: {}".format(exc))
            if self._subprocess.poll() is None:  # It could be that Ffmpeg is just slow to quit, though...
                logger.warning("Force-terminating dangling ffmpeg subprocess")
                self._subprocess.terminate()

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
