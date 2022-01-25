from __future__ import annotations

import math
from io import BytesIO
from typing import List
from typing import Tuple

from PIL import Image, ImageSequence

from src import gif_utilities
from src.execution import task
from src.handler import base
from src.util import decorator
from src.util.aux import fix_start_end_swap


class GifCutHandler(base.BaseCutHandler):
    # @decorator.create_hook(pre=None, post=base.post_cut_hook)
    def cut(self, stream: BytesIO, config: task.TaskConfig) -> Tuple[List[Image], float]:
        start_ms = config.start
        end_ms = config.end
        watermark = config.watermark
        duration = config.duration
        ext = config.extension

        stream.seek(0)
        image: Image = Image.open(stream)
        if duration is None:
            duration = gif_utilities.get_gif_duration(image=image)

        start_ms, end_ms = fix_start_end_swap(start=start_ms, end=end_ms)
        start_ms = max(start_ms, 0)  # put a realistic lower bound on end
        duration_ms = duration * 1000
        end_ms = min(end_ms or math.inf, duration_ms)  # put a realistic upper bound on end
        target_duration_ms = end_ms - start_ms

        # multiply duration by 1000 to have it in ms rather than s
        assert 0 < target_duration_ms < duration_ms and end_ms <= duration_ms  # sanity check

        frames_out: List[Image.Image] = []
        for frame in ImageSequence.Iterator(image):
            frame = frame.convert('RGB')
            frames_out.append(watermark(frame))
        assert len(frames_out) > 0
        return frames_out, target_duration_ms / (1000 * len(frames_out))
