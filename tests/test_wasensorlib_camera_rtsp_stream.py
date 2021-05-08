import tempfile

import functools
from datetime import datetime

from _scaffolding_utilities import check_periodic_stream_pusher_basic_behaviour
from wasensorlib.camera.rtsp_stream import RtspCameraSensor
from ffprobe import FFProbe


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


def test_rtsp_stream_standard_workflow():

    video_stream_url = "rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mov"  # Must exist on the Web
    sensor_class = functools.partial(RtspCameraSensor, video_stream_url=video_stream_url)

    tarfile_record_dicts = check_periodic_stream_pusher_basic_behaviour(
            sensor_class=sensor_class, recording_interval_s=10, total_recording_time_s=16)

    assert len(tarfile_record_dicts) == 2, tarfile_record_dicts

    for tarfile_record_dict in tarfile_record_dicts:
        assert tarfile_record_dict["extension"] == ".mp4"
        ffprobe_result = get_ffprobe_result_from_buffer(tarfile_record_dict["data"])
        media_length_s = get_media_length_s(ffprobe_result)
        assert 4 <= media_length_s <= 11
        video_stream = ffprobe_result.video[0]
        assert video_stream.codec_name == 'h264'
