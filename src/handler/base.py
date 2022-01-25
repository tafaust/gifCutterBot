from __future__ import annotations

import abc
from io import BytesIO
from typing import List
from typing import Tuple

from PIL.GifImagePlugin import GifImageFile
from PIL import Image as ImageModule
from PIL.Image import Image

from src.execution import task


def pre_cut_hook(stream: BytesIO, config: task.TaskConfig):
    pass


def post_cut_hook(r: Tuple[List[Image], float]) -> GifImageFile:
    # with BytesIO() as output:
    output = BytesIO()
    r[0][0].save(
            output,
            format='GIF',
            save_all=True,
            append_images=r[0][1:],
            optimize=False,
            duration=r[1],
            loop=0
    )
    gif: GifImageFile = ImageModule.open(output)
    return gif


class BaseCutHandler(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def cut(self, stream: BytesIO, config: task.TaskConfig) -> Tuple[List[Image], float]: ...
