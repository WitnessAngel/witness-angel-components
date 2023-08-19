import tempfile
from datetime import datetime

import time
from ffprobe import FFProbe

from wacomponents.sensors.camera.rtsp_stream import PeriodicStreamPusher
from wacryptolib.cryptainer import CryptainerStorage
from wacryptolib.sensor import TarfileRecordAggregator


# FIXME REMOVE THIS USELESS
class FakeTestCryptainerStorage(CryptainerStorage):
    """Fake class which bypasses encryption and forces filename unicity regardless of datetime, to speed up tests..."""

    increment = 0

    def enqueue_file_for_encryption(self, filename_base, payload, **kwargs):
        super().enqueue_file_for_encryption(filename_base + (".%03d" % self.increment), payload, **kwargs)
        self.increment += 1

    def _encrypt_payload_into_cryptainer(self, payload, **kwargs):
        return dict(payload_ciphertext_struct=payload)  # Not a real struct!

    def _decrypt_payload_from_cryptainer(self, cryptainer, **kwargs):
        return cryptainer["payload_ciphertext_struct"]  # Not a real struct!


# FIXME REMOVE THIS USELESS
class FakeTarfileRecordAggregator(TarfileRecordAggregator):  # USELESS ????
    def __init__(self):
        self._test_records = []

    def add_record(self, **kwargs):
        print("FakeTarfileRecordAggregator->add_record()")
        self._test_records.append(kwargs)

    def finalize_tarfile(self):
        print("FakeTarfileRecordAggregator->finalize_tarfile()")
        self._test_records = []



def check_periodic_stream_pusher_basic_behaviour(sensor_class: PeriodicStreamPusher, recording_interval_s: float, total_recording_time_s: float):

    """
    offload_payload_ciphertext = random().choice((True, False))
    container_storage = FakeTestCryptainerStorage(
        default_cryptoconf={"zexcsc": True},
        containers_dir=containers_dir,
        offload_payload_ciphertext=offload_payload_ciphertext,
    )
    """

    tarfile_aggregator = FakeTarfileRecordAggregator()  #container_storage=container_storage, max_duration_s=100)

    sensor = sensor_class(interval_s=recording_interval_s, tarfile_aggregator=tarfile_aggregator)

    sensor.start()

    time.sleep(total_recording_time_s)

    sensor.stop()
    sensor.join()

    records = tarfile_aggregator._test_records
    assert records, records  # At least one chunk is recorded

    return records




##### FFPROBE MEDIA CHECKING UTILITIES #####


def get_media_length_s(ffprobe_result: FFProbe) -> int:
    duration_str = ffprobe_result.metadata["Duration"]
    timedelta = datetime.strptime(duration_str, "%H:%M:%S.%f") - datetime.strptime("00:00", "%H:%M")
    return timedelta.total_seconds()


def get_ffprobe_result_from_buffer(buffer: bytes) -> FFProbe:
    fd, filename = tempfile.mkstemp()
    with open(fd, 'wb') as f:
        f.write(buffer)  # fd is autoclosed after this
    ffprobe_result = FFProbe(filename)
    return ffprobe_result

