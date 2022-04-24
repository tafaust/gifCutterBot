import math
import os
import re
from dataclasses import dataclass
from io import BytesIO
from typing import Dict, Callable, Tuple
from typing import List
from typing import Optional
from typing import Union
from urllib.parse import parse_qs, urlparse

import PIL
import requests
from PIL.Image import Image
from asyncpraw.models import Message
from asyncpraw.models import Submission
from bs4 import BeautifulSoup

import src.handler as handler_pkg
import src.model.result as result_pkg
from src.model.media_type import MediaType
from src.model.task_state import TaskConfigState
from src.model.task_state import TaskState
from src.util import exception, gif_utilities
from src.util.aux import Watermark
from src.util.aux import noop_image, fix_start_end_swap
from src.util.aux import watermark_image
from src.util.exception import TaskFailureException, OembedFailureException
from src.util.logger import root_logger, task_logger


@dataclass
class TaskConfig:
    """A task configuration which is not serializable.

    Attributes:
        message         The reddit message object.
        media_type      The media type of the resource requested for cutting.
        start           The start time in milliseconds from where to cut the MediaType.
        end             The end time in milliseconds to stop the cut of the MediaType.
        watermark       An optional callable that watermarks the cut media.
        state           The state of this :class:~`TaskConfig`.
        is_oembed       A flag indicating if the media is embedded via the oEmbed format (https://oembed.com/).
        is_video        A flag indicating if the media is a video.
        is_gif          A flag indicating if the media is a gif.
        is_crosspost    A flag indicating if the media is crossposted.
        media_url       The url to the media.
        duration        The total duration of the media in seconds read from the `message`.
        extension       The file extension of the media.
    """
    message: Message
    media_type: MediaType
    start: float
    end: Optional[float]
    watermark: Callable[[PIL.Image.Image], PIL.Image.Image]

    def __init__(
            self, message: Message, start: float, end: Optional[float], media_type: MediaType, watermark:
            Optional[Watermark] = None
    ):
        self.message = message
        self.media_type = media_type
        self.__is_video = self.media_type in [MediaType.MP4, MediaType.MOV, MediaType.WEBM]
        self.__is_gif = self.media_type == MediaType.GIF
        if hasattr(message.submission, 'crosspost_parent'):
            self.__is_crosspost = message.submission.crosspost_parent is not None
        else:
            self.__is_crosspost = False
        start_ms, end_ms = fix_start_end_swap(start=start, end=end)
        start_ms = max(start_ms, 0)  # put a realistic lower bound on end
        if self.duration is not None:
            # duration could be None here, will be computed in the specific handler
            end_ms = min(end_ms or math.inf, self.duration * 1000)  # put a realistic upper bound on end
        self.start = start_ms
        self.end = end_ms
        self.watermark = noop_image if watermark is None else lambda img: watermark_image(img, watermark)
        self._state = TaskConfigState.VALID

    def __repr__(self) -> str:
        return f'TaskConfig(message: {self.message}, media_type: {self.media_type}, start: {self.start}, ' \
               f'end: {self.end}, watermark: {self.watermark}, state: {self.state}, is_oembed: {self.is_oembed}, ' \
               f'is_video: {self.is_video}, is_gif: {self.is_gif}, is_crosspost: {self.is_crosspost}, ' \
               f'duration: {self.duration}, extension: {self.extension}, media_url: {self.media_url})'

    @property
    def state(self) -> TaskConfigState:
        return self._state

    def is_state(self, state: Union[TaskConfigState, List[TaskConfigState]]) -> bool:
        return self._state in state if state is List else self._state == state

    @property
    def is_oembed(self) -> bool:
        # full oembed spec: https://oembed.com/#section2
        # media is a dynamic attribute on submission
        if not hasattr(self.message.submission, 'media'):
            return False
        return bool(self.message.submission.media.get('oembed', False))

    @property
    def is_video(self) -> bool:
        return self.__is_video

    @property
    def is_gif(self) -> bool:
        return self.__is_gif

    @property
    def is_crosspost(self) -> bool:
        return self.__is_crosspost

    @property
    def media_url(self) -> str:
        # todo do this in __init__ and store in a "_variable"
        _submission: Submission = self.message.submission
        if self.is_oembed:
            return self.__get_oembed()[0]
        elif self.is_gif:
            if self.is_crosspost:
                return ''  # todo
            else:
                return _submission.url
        elif self.is_video:
            if self.is_crosspost:
                reddit_video = _submission.crosspost_parent_list[0].get('secure_media').get('reddit_video')
            else:
                reddit_video = _submission.secure_media.get('reddit_video', {})
            media_url = reddit_video.get('fallback_url', '')
            if media_url == '':
                self._state = TaskConfigState.INVALID
            return media_url
        else:
            raise exception.TaskConfigFailureException('Cannot parse attribute media_url.')

    @property
    def duration(self) -> Optional[float]:
        # todo do this in __init__ and store in a "_variable"
        if self.is_gif:
            # AFAIK there is no duration sent when we are dealing with a GIF
            with requests.get(self.media_url, stream=True) as resp:
                if resp.ok:
                    self._state = TaskConfigState.VALID
                    # read whole file via StreamReader into BytesIO
                    _stream = BytesIO(resp.raw.read())
                    _stream.seek(0)
                    return gif_utilities.get_gif_duration(image=PIL.Image.open(_stream))
                else:
                    self._state = TaskConfigState.INVALID
                    return math.nan
        elif self.is_video:
            _submission: Submission = self.message.submission
            if self.is_crosspost:
                reddit_video = _submission.crosspost_parent_list[0].get('secure_media').get('reddit_video')
            else:
                reddit_video = _submission.secure_media.get('reddit_video', {})
            return reddit_video.get('duration')
        else:
            # self._state = TaskState.INVALID  # duration will be computed in the specific handler if None
            return None

    @property
    def extension(self) -> Optional[str]:
        # todo do this in __init__ and store in a "_variable"
        ext: Optional[str]
        _submission: Submission = self.message.submission
        if self.is_oembed:
            return self.__get_oembed()[-1]
        elif self.is_gif:
            if self.is_crosspost:
                ext = None  # todo how to handle crossposted gifs?
            else:
                ext = os.path.splitext(_submission.url)[-1][1:]
        elif self.is_video:
            if self.is_crosspost:
                # todo make sure it always works with index 0 (should be the first post)
                reddit_video = _submission.crosspost_parent_list[0].get('secure_media').get('reddit_video')
            else:
                reddit_video = _submission.secure_media.get('reddit_video', {})
            ext = os.path.splitext(reddit_video.get('scrubber_media_url', [' ']))[-1][1:]
        else:
            self._state = TaskState.INVALID
            ext = None
        if ext == '' or ext is None:
            ext = None
            self._state = TaskConfigState.INVALID
        return ext

    def __get_oembed(self) -> Tuple[str, str, str]:
        """Returns a tuple with the source url, the media MIME-type and the media extension.
        """
        oembed: Dict = self.message.submission.media.get('oembed', {})
        html_string: str
        try:
            html_string = oembed['html']
        except KeyError:
            html_string = oembed['url']
        if not isinstance(html_string, str):
            task_logger.error('Failed to obtain the HTML of the oEmbed.')
        soup = BeautifulSoup(html_string, features='html.parser')
        try:
            # todo proper error handling! this has only been validated with
            src_url = parse_qs(urlparse(soup.iframe.get('src'))[4]).get('src')[0]
            another_soup = BeautifulSoup(requests.get(src_url).content, features='html.parser')
            source_tag = another_soup.video.findAll(name='source')[1]
            ext: str = os.path.splitext(source_tag['src'])[-1][1:]
            return source_tag['src'], source_tag['type'], ext
        except Exception as ex:
            task_logger.error(f'Encountered oEmbed provider {oembed.get("provider_name")}.\n{ex}')
            raise OembedFailureException()


class TaskConfigFactory(TaskConfig):
    state: TaskConfigState = TaskConfigState.VALID

    @classmethod
    def from_message(cls, message: Message) -> TaskConfig:
        _config = {
            'message': message,
            'media_type': cls.__get_media_type(message),
            **cls.__parse_start_and_end(message),
        }
        return TaskConfig(**_config)

    @classmethod
    def __is_crosspost(cls, message: Message) -> bool:
        if hasattr(message.submission, 'crosspost_parent'):
            return message.submission.crosspost_parent is not None
        return False

    @classmethod
    def __is_video(cls, message: Message) -> bool:
        if cls.__is_crosspost(message=message):
            return message.submission.crosspost_parent_list[-1].get('is_video', False)
        return message.submission.is_video

    @classmethod
    def __is_gif(cls, message: Message) -> bool:
        if cls.__is_crosspost(message=message):
            return False  # todo
        if message.submission.url:
            return os.path.splitext(message.submission.url)[-1][1:] == 'gif'
        return False

    @classmethod
    def __is_oembed(cls, message: Message):
        # full oembed spec: https://oembed.com/#section2
        # media is a dynamic attribute on submission
        if not hasattr(message.submission, 'media'):
            return False
        return bool(message.submission.media.get('oembed', False))

    @classmethod
    def __parse_start_and_end(cls, message: Message) -> Dict[str, float]:
        params = {}
        pattern = re.compile(r'(s|start)=([\d]+) (e|end)=([\d]+)', re.IGNORECASE)
        matches = pattern.search(message.body)
        if matches is None:
            root_logger.warning('Skipping message because no match was found.')
            cls.state = TaskConfigState.INVALID
            return {}
        root_logger.debug(f'Found pattern matches: {matches.groups()}')
        params['start'] = int(matches.group(2))
        params['end'] = int(matches.group(4))
        return params

    @classmethod
    def __get_media_type(cls, message: Message) -> Union[MediaType, None]:
        if cls.__is_video(message=message):
            # get video from original post (apparently we can only get it from there so we do the the backtrace)
            if cls.__is_crosspost(message=message):
                reddit_video = message.submission.crosspost_parent_list[0].get('secure_media').get('reddit_video')
            else:
                reddit_video = message.submission.secure_media.get('reddit_video', {})
            ext: str = os.path.splitext(reddit_video.get('scrubber_media_url', [' ']))[-1][1:]
            if ext == '':
                cls.state = TaskConfigState.INVALID
                return None
            return MediaType[ext.upper()]
        elif cls.__is_gif(message=message):
            return MediaType.GIF
        elif cls.__is_oembed(message=message):
            oembed: Dict = message.submission.media.get('oembed', {})
            html_string: str
            try:
                html_string = oembed['html']
            except KeyError:
                html_string = oembed['url']
            if not isinstance(html_string, str):
                task_logger.error('Failed to obtain the HTML of the oEmbed.')
            soup = BeautifulSoup(html_string, features='html.parser')
            try:
                # todo proper error handling! this has only been validated with
                src_url = parse_qs(urlparse(soup.iframe.get('src'))[4]).get('src')[0]
                another_soup = BeautifulSoup(requests.get(src_url).content, features='html.parser')
                source_tag = another_soup.video.findAll(name='source')[1]
                ext: str = os.path.splitext(source_tag['src'])[-1][1:]
                return MediaType[ext.upper()]
            except Exception as ex:
                task_logger.error(f'Encountered oEmbed provider {oembed.get("provider_name")}.\n{ex}')
        else:
            cls.state = TaskConfigState.INVALID
            return None


class Task(object):
    def __init__(self, config: TaskConfig):
        self.__config: TaskConfig = config
        self._task_state = TaskState.VALID
        self._select_handler()

    def __call__(self, *args, **kwargs):
        return self.handle()

    @property
    def state(self):
        return self._task_state

    def is_state(self, state: Union[TaskState, List[TaskState]]) -> bool:
        if state is List:
            return self._task_state in state
        return self._task_state == state

    def _select_handler(self):
        mt: MediaType = self.__config.media_type
        if mt == MediaType.GIF:
            self._task_handler = handler_pkg.gif.GifCutHandler()
        elif mt in [MediaType.MP4, MediaType.MOV, MediaType.WEBM]:
            self._task_handler = handler_pkg.video.VideoCutHandler()
        else:
            self._task_state = TaskState.DROP
            # self._task_handler = TestCutHandler()
            root_logger.warning(f'No handler for media type: {mt}')

    def handle(self) -> result_pkg.Result:
        _stream: Optional[BytesIO] = self._fetch_stream()
        if self._task_state == TaskState.INVALID:
            raise TaskFailureException('Failed to fetch stream from host!')
        _result: result_pkg.Result = self._task_handler.cut(stream=_stream, config=self.__config)
        self._task_state = TaskState.DONE
        return _result

    def _fetch_stream(self) -> Optional[BytesIO]:
        _stream: BytesIO
        media_url: str = self.__config.media_url
        with requests.get(media_url, stream=True) as r:
            if r.status_code == 200:
                self._task_state = TaskState.VALID
                _stream = BytesIO(r.raw.read())
            else:
                self._task_state = TaskState.INVALID
                return None
        return _stream

    @property
    def config(self):
        return self.__config
