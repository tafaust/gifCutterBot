from typing import Tuple

from PIL.Image import Image
from PIL.ImageDraw import ImageDraw


noop_image = lambda image: image


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
