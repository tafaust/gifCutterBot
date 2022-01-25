import os
import re
from io import BytesIO
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

import requests
from PIL.GifImagePlugin import GifImageFile
from PIL.Image import Image
from praw.models import Message
from praw.models import Submission

from src.handler import base
from src.handler.gif import GifCutHandler
from src.handler.video import VideoCutHandler
from src.model.media_type import MediaType
from src.model.task_state import TaskConfigState
from src.model.task_state import TaskState
from src.util import exception
from src.util.aux import noop_image
from src.util.aux import Watermark
from src.util.aux import watermark_image
from src.util.exception import TaskFailureException
from src.util.logger import root_logger


class TaskConfig(object):
    def __init__(
            self, message: Message, start: float, end: float, media_type: MediaType, watermark:
            Optional[Watermark] = None
    ):
        self.message = message
        self.media_type = media_type
        self.start = start
        self.end = end
        self.watermark = noop_image if watermark is None else lambda img: watermark_image(img, watermark)
        self._state = TaskConfigState.VALID

        self.__is_video = self.media_type in [MediaType.MP4, MediaType.MOV, MediaType.WEBM]
        self.__is_gif = self.media_type == MediaType.GIF
        if hasattr(message.submission, 'crosspost_parent'):
            self.__is_crosspost = self.message.submission.crosspost_parent is not None
        else:
            self.__is_crosspost = False

        # there is no advantage in using a slotted class, thus resorting to __dict__
        # self.__dict__ = {
        #     'message': self.message,
        #     'media_type': self.media_type,
        #     'start': self.start,
        #     'end': self.end,
        #     'watermark': self.watermark,
        #     'state': self.state,
        #     'is_video': self.is_video,
        #     'is_gif': self.is_gif,
        #     'is_crosspost': self.is_crosspost,
        # }

    # def __getattr__(self, values):
    #     yield from [getattr(self, i) for i in values.split('_')]

    def __str__(self) -> str:
        return f'TaskConfig(message: {self.message}, media_type: {self.media_type}, start: {self.start}, ' \
               f'end: {self.end}, watermark: {self.watermark}, state: {self.state}, is_video: {self.is_video}, ' \
               f'is_gif: {self.is_gif}, is_crosspost: {self.is_crosspost}, duration: {self.duration}, extension: ' \
               f'{self.extension}, media_url: {self.media_url})'

    @property
    def state(self) -> TaskConfigState:
        return self._state

    def is_state(self, state: Union[TaskConfigState, List[TaskConfigState]]) -> bool:
        return self._state in state if state is List else self._state == state

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
        if self.is_gif:
            if self.is_crosspost:
                return ''  # dunno
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
            return None
        elif self.is_video:
            _submission: Submission = self.message.submission
            if self.is_crosspost:
                reddit_video = _submission.crosspost_parent_list[0].get('secure_media').get('reddit_video')
            else:
                reddit_video = _submission.secure_media.get('reddit_video', {})
            return reddit_video.get('duration')
        else:
            self._state = TaskState.INVALID
            return None

    @property
    def extension(self) -> Optional[str]:
        # todo do this in __init__ and store in a "_variable"
        ext: Optional[str]
        _submission: Submission = self.message.submission
        if self.is_gif:
            if self.is_crosspost:
                ext = None  # todo
            else:
                ext = os.path.splitext(_submission.url)[-1][1:]
        elif self.is_video:
            if self.is_crosspost:
                # todo index 0?
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


class TaskConfigFactory(TaskConfig):
    state: TaskConfigState = TaskConfigState.VALID

    @classmethod
    def from_message(cls, message: Message) -> TaskConfig:
        _config = {
            'message': message,
            'media_type': cls.__get_media_type(message),
            **cls.__parse_start_and_end(message),
        }
        return cls(**_config)

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
    def __parse_start_and_end(cls, message: Message) -> Dict[str, float]:
        params = {}
        pattern = re.compile(r'(s|start)=([\d]+) (e|end)=([\d]+)', re.IGNORECASE)
        matches = pattern.search(message.body)
        if matches is None:
            root_logger.warn('Skipping message because no match was found.')
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
            self._task_handler = GifCutHandler()
        elif mt in [MediaType.MP4, MediaType.MOV, MediaType.WEBM]:
            self._task_handler = VideoCutHandler()
        else:
            self._task_state = TaskState.DROP
            # self._task_handler = TestCutHandler()
            root_logger.warn(f'No handler for media type: {mt}')

    def handle(self) -> Tuple[GifImageFile, float]:
        _stream: Optional[BytesIO] = self._fetch_stream()
        if self._task_state == TaskState.INVALID:
            raise TaskFailureException('Failed to fetch stream from host!')
        image: List[Image]
        avg_fps: float
        image, avg_fps = self._task_handler.cut(stream=_stream, config=self.__config)
        gif: GifImageFile = base.post_cut_hook(r=(image, avg_fps))
        self._task_state = TaskState.DONE
        return gif, avg_fps

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
        # if self.__config.is_video:
        #     with open(f'foo.mp4', 'wb') as f:
        #         f.write(requests.get(url, stream=True).raw.read())
        #     with open(f'foo.mp4', 'rb') as f:
        #         _stream = BytesIO(f.read())
        # elif self.__config.is_gif:
        #     with requests.get(url, stream=True) as r:
        #         _stream = Image.open(r.raw)
        # else:
        #     root_logger.error('No valid input! Neither received a video or gif.')

    @property
    def config(self):
        return self.__config
