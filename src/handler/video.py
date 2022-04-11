from __future__ import annotations

import shlex
import subprocess
from io import BytesIO
from tempfile import NamedTemporaryFile

import src.model.result as result
from src import video_utilities
from src.execution import task
from src.handler import base


class VideoCutHandler(base.BaseCutHandler):
    def cut(self, stream: BytesIO, config: task.TaskConfig) -> result.Result:
        start_ms = config.start
        end_ms = config.end
        watermark = config.watermark
        duration = config.duration
        ext = config.extension
        if duration is None:
            duration = video_utilities.get_vid_duration(stream)
        duration_ms = duration * 1000
        target_duration_ms = end_ms - start_ms
        assert 0 < target_duration_ms < duration_ms and end_ms <= duration_ms  # sanity check
        # https://stackoverflow.com/questions/18444194/cutting-the-videos-based-on-start-and-end-time-using-ffmpeg#comment51400781_18449609
        # movflags with empty_moov: https://stackoverflow.com/questions/25411836/ffmpeg-doesnt-work-with-mp4-and-stdout
        # seed before input is faster but less accurate; after input is slower but more accurate
        cut_cmd = shlex.split(
            f'ffmpeg -i pipe:0 -ss {start_ms / 1000} -movflags empty_moov -t {target_duration_ms / 1000} -c copy -f {ext} pipe:1'
        )
        # shaky videos converted to gif are huge (larger than 10MB) which makes it hard to upload them later on due to restrictions
        # f'ffmpeg -ss {start_ms / 1000} -t {target_duration_ms / 1000} -i pipe:0 -filter_complex "fps={fps},split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" -y -loop 0 -f gif pipe:1'
        # https://stackoverflow.com/questions/20321116/can-i-pipe-a-io-bytesio-stream-to-subprocess-popen-in-python#comment30326992_20321129
        proc = subprocess.Popen(cut_cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        stream.seek(0)
        out, err = proc.communicate(input=stream.read())
        proc.wait()
        response = err.decode()

        # sometimes, subprocess fails with BytesIO and we thus need to store the file temporarily on disk and retry
        if 'partial file' in response:
            # retry with temporary file instead of BytesIO
            with NamedTemporaryFile('wb', suffix=f'.{ext}') as f:
                stream.seek(0)
                f.write(stream.read())
                cut_cmd[2] = f.name  # replace pipe:0 with name of temporary file
                proc = subprocess.Popen(cut_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                out, _ = proc.communicate()
                proc.wait()

        media_stream = BytesIO(out)
        media_stream.seek(0)
        # todo watermark video (https://video.stackexchange.com/a/25575)
        # frames_out: List[Image.Image] = []
        # for frame in ImageSequence.Iterator(gif):
        #     frame = frame.convert('RGB')
        #     frames_out.append(watermark(frame))
        # assert len(frames_out) > 0
        _result: result.Result = result.Result(
            media_stream=media_stream,
            media_type=config.media_type,
            message=config.message,
        )
        return _result
        # return frames_out, target_duration_ms / (1000 * len(frames_out))
