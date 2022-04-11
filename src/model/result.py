import io
from dataclasses import dataclass
from typing import Optional

from asyncpraw.models import Message

from src.model.media_type import MediaType


@dataclass
class Result(object):
    media_stream: io.BytesIO
    media_type: MediaType
    message: Message
    upload_link: Optional[str]

    def __init__(
            self,
            media_stream: io.BytesIO,
            *,
            media_type: MediaType,
            message: Message,
            upload_link: Optional[str] = None,
    ):
        self.media_stream = media_stream
        self.media_type = media_type
        self._upload_link = upload_link
        self.message = message

    def __repr__(self):
        return f'Result(media_stream={self.media_stream}, media_type={self.media_type}, message={self.message}, upload_link={self._upload_link})'

    @property
    def upload_link(self) -> str:
        if self._upload_link is None:
            raise Exception('No upload link found when accessed!')  # todo custom exception
        return self._upload_link

    @upload_link.setter
    def upload_link(self, url: str):
        self._upload_link = url


'''
class Result(object):
    def __init__(self, message: Message, gif: GifImageFile, gif_duration):
        self._gif_link = None
        self._message = message
        self._gif = gif
        self._gif_duration = gif_duration  # fixme is this shit in ms or s!?

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
'''
