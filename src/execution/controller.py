import asyncio
from tempfile import NamedTemporaryFile
from typing import AsyncIterator, Optional
from typing import Union

from PIL.GifImagePlugin import GifImageFile
from asyncpraw.models import Message
from asyncpraw.reddit import Comment
from imgurpython import ImgurClient

import src.execution.task as t
from src.execution.result import Result
from src.client.reddit import RedditClient
from src.model.execution_mode import ExecutionMode
from src.model.task_state import TaskConfigState
from src.model.task_state import TaskState
from src.util import decorator, config
from src.util.exception import TaskFailureException
from src.util.logger import root_logger
from src.util.logger import upload_logger
from src.util.logger import cut_logger


def log_broad_exception(err, logger=cut_logger) -> None:
    logger.error(f'Unexpected error ({type(err).__name__}): {err}')


class AioController(object):
    # todo asyncio queue's: https://stackoverflow.com/a/24704950/2402281
    # todo reduce praw's Message model to make it pickle'able for multiprocessing.Queue to work
    input_queue: asyncio.Queue
    output_queue: asyncio.Queue

    def __init__(self, input_queue: asyncio.Queue, output_queue: asyncio.Queue,
                 mode: ExecutionMode = ExecutionMode.NORMAL):
        self._mode = mode
        self.output_queue = output_queue
        self.input_queue = input_queue
        self.reddit = None
        self.imgur = None

    def _init_reddit_host(self) -> None:
        if self.reddit is None:
            root_logger.info('Initializing async reddit client.')
            self.reddit: RedditClient = RedditClient()

    def _init_imgur_host(self) -> None:
        if self.imgur is None:
            root_logger.info('Initializing sync imgur client.')
            self.imgur: ImgurClient = ImgurClient(config.IMGUR_CLIENT_ID, config.IMGUR_CLIENT_SECRET)

    async def run(self, *args, **kwargs) -> None:
        self._init_reddit_host()
        root_logger.debug('Calling controller.run ...')
        await self.fetch()
        await self.work()
        await self.upload_and_answer()

    async def fetch(self) -> None:
        """Must not be called more than every 2 seconds to not violate reddit rate limits.
        """
        # todo custom logger
        self._init_reddit_host()
        root_logger.info('Fetching new messages...')
        try:
            await self._fill_task_queue_from_reddit()
        except Exception as err:
            log_broad_exception(err, root_logger)

    @decorator.run_in_executor
    def work(self) -> None:
        """Performs the work (GIF or VID cutting) on the input queue and writes the results in the output queue.
        """
        cut_logger.info('Working on input queue...')
        _task = self._read_from_input_queue()
        if _task is None:
            # todo modify controller state?
            return
        if _task.is_state([TaskState.DROP, TaskState.DONE]):
            cut_logger.info('Dropping task from input queue...')
            cut_logger.debug(f'Task: {_task}')
            return  # get already removed task from queue, just need to return
        elif _task.is_state(TaskState.INVALID):
            # put task back into input queue
            cut_logger.info('Task is invalid. Putting back into input queue...')
            cut_logger.debug(f'Task: {_task}')
            self.input_queue.put_nowait(_task)
        elif _task.is_state(TaskState.VALID):
            cut_logger.info('Task is valid. May the cutting begin!')
            _result = self._exert_task(task=_task)
            cut_logger.debug(f'Obtained task result: {_result}')
            _outcome = self._write_result_to_output_queue(result=_result)
            if _outcome:
                pass  # possible clean up

    # @decorator.run_in_executor
    async def upload_and_answer(self) -> None:
        if self._mode == ExecutionMode.TEST:
            _result: Result
            _result = self._read_result_from_output_queue()
            if _result is None:  # fixme
                return
            filename = 'test.gif'
            with open(filename, mode='wb') as fp:
                # save GIF into named temp file for upload with deprecated imgur lib...
                _result.gif.save(fp=fp, format='GIF', save_all=True, duration=_result.gif_duration)
            upload_logger.debug(f'Created file: {filename}')
            return
        self._init_imgur_host()
        self._init_reddit_host()
        _result: Result
        _result = self._read_result_from_output_queue()
        if _result is None:  # fixme
            upload_logger.warning('Received NoneType result.')
            return
        _result = self._upload_to_imgur(result=_result)
        await self._answer_in_reddit(result=_result)

    async def _fill_task_queue_from_reddit(self) -> None:
        if not await self.reddit.has_new_message():
            root_logger.info('No new message received.')
            return None
        messages: AsyncIterator[Union[Comment, Message]] = self.reddit.fetch_new_messages()
        async for message in messages:
            root_logger.info('New message received.')
            root_logger.debug(f'Received message: {message.body}')
            await self._reddit_message_to_input_queue(message=message)

    async def _reddit_message_to_input_queue(self, message: Message) -> None:
        await message.submission.load()  # fetch submission
        _task_config = t.TaskConfigFactory.from_message(message=message)
        root_logger.debug(f'Extracted task config from message: {_task_config}')
        if _task_config.is_state(TaskConfigState.INVALID):
            root_logger.warning('Task config state is invalid!')
            root_logger.debug(f'Task config: {_task_config}')
            return
        root_logger.info('Attempting to put task into input queue...')
        try:
            # Cannot use multiprocessing.Queue because can't pickle local object
            # 'UserSubreddit._dict_depreciated_wrapper.<locals>.wrapper' from Message
            await self.input_queue.put(t.Task(config=_task_config))
        except ValueError:
            root_logger.error(f'Queue is closed.')
        except asyncio.QueueFull:
            root_logger.error(f'Queue is full.')
            root_logger.debug(f'Input queue: {self.input_queue}')
        except Exception as err:
            log_broad_exception(err)
        else:
            await message.mark_read()
        root_logger.debug(f'Input queue size: {self.input_queue.qsize()}')

    def _read_from_input_queue(self) -> t.Task:
        _task: t.Task
        try:
            cut_logger.info('Attempting to immediately get task from input queue without blocking...')
            _task = self.input_queue.get_nowait()
        except ValueError:
            cut_logger.error(f'Queue is closed.')
        except asyncio.QueueEmpty:
            cut_logger.warning(f'Queue is empty.')
            cut_logger.debug(f'Input queue: {self.input_queue}')
        except Exception as err:
            log_broad_exception(err)
        else:
            return _task

    def _exert_task(self, task: t.Task) -> Result:
        if task.is_state(TaskState.VALID):
            _gif: GifImageFile
            cut_logger.info('Handling task...')
            try:
                _gif, _gif_duration = task.handle()
                return Result(message=task.config.message, gif=_gif, gif_duration=_gif_duration)
            except TaskFailureException as err:
                cut_logger.error(f'Task failed: {err}')
            except Exception as err:
                log_broad_exception(err)

    def _write_result_to_output_queue(self, result: Result) -> bool:
        try:
            cut_logger.info('Putting task result into output queue...')
            self.output_queue.put_nowait(result)
        except ValueError:
            cut_logger.error(f'Queue is closed.')
        except asyncio.QueueFull:
            cut_logger.error(f'Queue is full.')
            cut_logger.debug(f'Output queue: {self.output_queue}')
        except Exception as err:
            log_broad_exception(err)
        else:
            cut_logger.debug(f'Output queue size: {self.output_queue.qsize()}')
            return True
        return False

    def _read_result_from_output_queue(self) -> Optional[Result]:
        # todo custom logger
        _result: Result
        try:
            upload_logger.info('Attempting to immediately get task from output queue without blocking...')
            _result = self.output_queue.get_nowait()
        except ValueError:
            upload_logger.error(f'Queue is closed.')
        except asyncio.QueueEmpty:
            upload_logger.warning(f'Queue is empty.')
            upload_logger.debug(f'Output queue: {self.output_queue}')
        except Exception as err:
            log_broad_exception(err)
        else:
            return _result

    # @decorator.run_in_executor
    def _upload_to_imgur(self, result: Result) -> Result:
        # todo custom logger
        # todo worth to have this async because of io
        with NamedTemporaryFile(mode='wb', suffix='.gif') as fp:
            # save GIF into named temp file for upload with deprecated imgur lib...
            result.gif.save(fp=fp, format='GIF', save_all=True, duration=result.gif_duration)
            res = self.imgur.upload_from_path(path=fp.name, anon=False)
            upload_logger.debug(f'Upload to imgur: {res.get("link")}')
            # todo error handling with res
            result.gif_link = res.get('link')
        return result

    # @decorator.run_in_executor
    async def _answer_in_reddit(self, result: Result) -> None:
        # todo need a custom result data type to answer the message T_T
        # reply with link to the just cut gif and mark as unread
        issue_link = f'https://www.reddit.com/message/compose/?to=domac&subject={config.REDDIT_USERNAME}%20issue&message=' \
                     f'Add a link to the gif or comment in your message%2C I%27m not always sure which request is ' \
                     f'being reported. Thanks for helping me out! '
        bot_footer = f"---\n\n^(I am a bot.) [^(Report an issue)]({issue_link})"
        await result.message.reply(f'Here is your cut GIF: {result.gif_link}\n{bot_footer}')
        # m.mark_read()  # done
        upload_logger.info('Reddit reply sent!')
