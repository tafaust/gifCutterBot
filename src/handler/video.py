from __future__ import annotations

import math
import shlex
import subprocess
from io import BytesIO
from tempfile import NamedTemporaryFile
from typing import List
from typing import Tuple

from PIL import Image
from PIL import ImageSequence

from src import video_utilities
from src.execution import task
from src.handler import base
from src.util.aux import fix_start_end_swap


class VideoCutHandler(base.BaseCutHandler):
    # @decorator.create_hook(pre=None, post=base.post_cut_hook)
    def cut(self, stream: BytesIO, config: task.TaskConfig) -> Tuple[List[Image.Image], float]:
        start_ms = config.start
        end_ms = config.end
        watermark = config.watermark
        duration = config.duration
        ext = config.extension

        if duration is None:
            duration = video_utilities.get_vid_duration(stream)

        start_ms, end_ms = fix_start_end_swap(start=start_ms, end=end_ms)
        start_ms = max(start_ms, 0)  # put a realistic lower bound on end
        duration_ms = duration * 1000
        end_ms = min(end_ms or math.inf, duration_ms)  # put a realistic upper bound on end
        target_duration_ms = end_ms - start_ms

        # multiply duration by 1000 to have it in ms rather than s
        assert 0 < target_duration_ms < duration_ms and end_ms <= duration_ms  # sanity check

        fps = video_utilities.get_frame_rate(stream)
        ffmpeg = 'ffmpeg'
        # https://stackoverflow.com/questions/18444194/cutting-the-videos-based-on-start-and-end-time-using-ffmpeg#comment51400781_18449609
        cut_cmd = shlex.split(
                f'{ffmpeg} -ss {start_ms / 1000} -t {target_duration_ms / 1000} -i pipe:0 -filter_complex "fps={fps},split[a][b];[a]palettegen[p];[b][p]paletteuse" -y -loop 0 -f gif pipe:1'
        )
        # https://stackoverflow.com/questions/20321116/can-i-pipe-a-io-bytesio-stream-to-subprocess-popen-in-python#comment30326992_20321129
        proc = subprocess.Popen(cut_cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        stream.seek(0)
        out, err = proc.communicate(input=stream.read())
        proc.wait()
        response = err.decode()

        if 'partial file' in response:
            # retry with temporary file instead of BytesIO
            with NamedTemporaryFile('wb', suffix=f'.{ext}') as f:
                stream.seek(0)
                f.write(stream.read())
                cut_cmd[6] = f.name
                proc = subprocess.Popen(cut_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                out, _ = proc.communicate()
                proc.wait()

        gif = Image.open(BytesIO(out))

        frames_out: List[Image.Image] = []
        for frame in ImageSequence.Iterator(gif):
            frame = frame.convert('RGB')
            frames_out.append(watermark(frame))
        assert len(frames_out) > 0
        return frames_out, target_duration_ms / (1000 * len(frames_out))
