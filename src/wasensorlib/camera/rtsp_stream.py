import subprocess
import threading

from datetime import timezone, datetime
from kivy.logger import Logger as logger

from wacryptolib.sensor import TarfileRecordsAggregator
from wacryptolib.utilities import PeriodicTaskHandler, synchronized, get_utc_now_date

import io


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
        #self._lock = threading.Lock() ??

    @synchronized
    def start(self):
        """
        FR : Methode qui permet de ne pas redémarrer une deuxième fois l'enregistrement'

        """
        super().start()

        logger.info(">>> Starting sensor %s" % self)

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

        assert from_datetime and to_datetime, (from_datetime, to_datetime)

        self._tarfile_aggregator.add_record(
            sensor_name=self.sensor_name,
            from_datetime=from_datetime,
            to_datetime=to_datetime,
            extension=self.file_extension,
            data=data,
        )

    @synchronized
    def _offloaded_run_task(self):

        if not self.is_running:
            return

        from_datetime = self._current_start_time
        to_datetime = datetime.now(tz=timezone.utc)

        data = self._do_stop_recording() # Renames target files
        self._do_start_recording()  # Must be restarded imediately

        self._do_push_buffer_file_to_aggregator(data=data, from_datetime=from_datetime, to_datetime=to_datetime)




class RtspCameraSensor(PeriodicStreamPusher):

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
            "-rtsp_transport",
            "tcp"]
        codec = [
            "-vcodec",
            "copy",
            "-acodec",
            "copy",
            "-map",
            "0"]
        logs = [
            "-loglevel",
            "warning"
        ]
        output = [
            "pipe:1"  # Pipe to stdout
        ]

        pipeline = exec + self.input + codec + self.recording_duration + self.format_params + logs + output

        logger.info("Calling RtspCameraSensor subprocess command: {}".format(" ".join(pipeline)))
        self._subprocess = subprocess.Popen(pipeline,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=None)  # Stderr is left floating for now

        self._stdout_buff = []
        self._stdout_thread = threading.Thread(target=self._subprocess._readerthread,
                                                args=(self._subprocess.stdout, self._stdout_buff))


        #returncode = self.process.wait()
        #if returncode:
        #    logger.warning("recorder process exited with abnormal code %s", returncode)

    def _do_start_recording(self):
        self._launch_and_wait_ffmpeg_process()

    def _do_stop_recording(self):
        self._subprocess.stdin.write("q")  # FFMPEG command to quit
        self._subprocess.close()
        self._stdout_thread.join(timeout=10)
        return self._stdout_buff[0] if self._stdout_buff else b""

