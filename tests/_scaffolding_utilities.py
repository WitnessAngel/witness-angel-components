import time
from random import random

from wacryptolib.container import ContainerStorage
from wacryptolib.sensor import TarfileRecordsAggregator
from wasensorlib.camera.rtsp_stream import PeriodicStreamPusher


class FakeTestContainerStorage(ContainerStorage):
    """Fake class which bypasses encryption and forces filename unicity regardless of datetime, to speed up tests..."""

    increment = 0

    def enqueue_file_for_encryption(self, filename_base, data, **kwargs):
        super().enqueue_file_for_encryption(filename_base + (".%03d" % self.increment), data, **kwargs)
        self.increment += 1

    def _encrypt_data_into_container(self, data, **kwargs):
        return dict(data_ciphertext=data)

    def _decrypt_data_from_container(self, container, **kwargs):
        return container["data_ciphertext"]


class FakeTarfileRecordsAggregator(TarfileRecordsAggregator):  # USELESS ????
    def __init__(self):
        self._test_records = []

    def add_record(self, **kwargs):
        print("FakeTarfileRecordsAggregator->add_record()")
        self._test_records.append(kwargs)

    def finalize_tarfile(self):
        print("FakeTarfileRecordsAggregator->finalize_tarfile()")
        self._test_records = []



def check_periodic_stream_pusher_basic_behaviour(sensor_class: PeriodicStreamPusher, recording_interval_s: float, total_recording_time_s: float):

    """
    offload_data_ciphertext = random().choice((True, False))
    container_storage = FakeTestContainerStorage(
        default_encryption_conf={"zexcsc": True},
        containers_dir=containers_dir,
        offload_data_ciphertext=offload_data_ciphertext,
    )
    """

    tarfile_aggregator = FakeTarfileRecordsAggregator()  #container_storage=container_storage, max_duration_s=100)

    sensor = sensor_class(interval_s=recording_interval_s, tarfile_aggregator=tarfile_aggregator)

    sensor.start()

    time.sleep(total_recording_time_s)

    sensor.stop()
    sensor.join()

    records = tarfile_aggregator._test_records
    assert records, records  # At least one chunk is recorded

    return records

