from PIL.GifImagePlugin import GifImageFile
from asyncpraw.models import Message

from src.execution.task import TaskConfig


class Result(object):
    def __init__(self, message: Message, gif: GifImageFile, gif_duration):
        self._gif_link = None
        self._message = message
        self._gif = gif
        self._gif_duration = gif_duration

    @property
    def message(self):
        return self._message

    @property
    def gif(self):
        return self._gif

    @property
    def gif_duration(self):
        return self._gif_duration

    @property
    def gif_link(self):
        if self._gif_link is None:
            raise Exception('No GIF link found when accessed!')  # todo custom exception
        return self._gif_link

    @gif_link.setter
    def gif_link(self, url: str):
        self._gif_link = url
