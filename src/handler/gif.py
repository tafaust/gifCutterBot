from __future__ import annotations

import math
from io import BytesIO
from typing import List

import PIL
import PIL.Image
import PIL.ImageSequence
import PIL.GifImagePlugin

import src.model.result as result
from src import gif_utilities
from src.execution import task
from src.handler import base
from src.model.media_type import MediaType


class GifCutHandler(base.BaseCutHandler):
    # @decorator.create_hook(pre=None, post=base.post_cut_hook)
    def cut(self, stream: BytesIO, config: task.TaskConfig) -> result.Result:
        start_ms = config.start
        end_ms = config.end
        watermark = config.watermark
        duration = config.duration

        stream.seek(0)
        image: PIL.Image = PIL.Image.open(stream)
        if duration is None:
            duration = gif_utilities.get_gif_duration(image=image)
            end_ms = min(end_ms or math.inf, duration * 1000)  # put a realistic upper bound on end
        # duration_ms = duration * 1000
        target_duration_ms = end_ms - start_ms
        # assert 0 < target_duration_ms < duration_ms and end_ms <= duration_ms  # sanity check
        # iterate GIF frames and optionally apply watermark
        frames: List[PIL.Image.Image] = []
        cum_duration_ms = 0
        frame: PIL.Image.Image
        for frame in PIL.ImageSequence.Iterator(image):
            # https://pillow.readthedocs.io/en/latest/handbook/image-file-formats.html#gif
            if cum_duration_ms < start_ms:
                cum_duration_ms += frame.info['duration']
                continue
            if cum_duration_ms < start_ms + end_ms:
                frames.append(watermark(frame.convert('RGB')))
                cum_duration_ms += frame.info['duration']
            elif len(frames) == 0:
                # special case: diff is too small that we just have to take a single frame
                # if end_ms - start_ms < frame.info['frame_duration']:
                frames.append(watermark(frame.convert('RGB')))
                break
            else:
                break  # early stopping
        assert len(frames) > 0  # sanity check that there is at least one frame
        _result: result.Result
        gif_duration_seconds = target_duration_ms / (1000 * len(frames))  # average frame duration
        output = BytesIO()
        frames[0].save(
            output,
            format='GIF',
            save_all=True,
            append_images=frames[1:],
            optimize=False,
            duration=gif_duration_seconds,
            loop=0
        )
        # gif: PIL.GifImagePlugin.GifImageFile = PIL.Image.open(output)
        return result.Result(
            media_stream=output,
            media_type=MediaType.GIF,
            message=config.message,
            # gif_duration=gif_duration_seconds,
        )
