from typing import Tuple

import PIL.GifImagePlugin
from PIL import ImageDraw
from PIL.Image import Image


# fixme refactor into individual files


def noop_image(image: Image) -> Image:
    return image


class Watermark:
    position = (0, 0)
    text = ''
    color = (255, 255, 255)

    def __init__(self, text: str, position: Tuple[int, int], color: Tuple[int, int, int]):
        self.text = text
        self.position = position
        self.color = color


def watermark_image(image: Image, watermark: Watermark) -> Image:
    # todo assert check that watermark position is in image bounds
    draw = ImageDraw.Draw(image)
    draw.text(watermark.position, watermark.text, watermark.color)
    return image


def fix_start_end_swap(start: float, end: float) -> Tuple[float, float]:
    """Assigns the lower value to start and the larger value to end.

    Args:
        start: The parsed start time in milliseconds.
        end: The parsed end time in milliseconds.

    Returns:
        A tuple with start at first position and end at the last position.
    """
    return min(start, end), max(start, end)


def get_avg_fps(image: PIL.GifImagePlugin.GifImageFile) -> float:
    """ Returns the average framerate of a PIL Image object """
    image.seek(0)
    frames = duration = 0
    while True:
        try:
            frames += 1
            duration += image.info['duration']
            image.seek(image.tell() + 1)
        except EOFError:
            return frames / duration * 1000
