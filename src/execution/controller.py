import asyncio
import base64
from typing import AsyncIterator, Optional
from typing import Union

from asyncpraw.models import Message
from asyncpraw.reddit import Comment
# from imgurpython import ImgurClient

import src.execution.task as t
from src.client.imgur import ImgurClient
from src.model.result import Result
from src.client.reddit import RedditClient
from src.model.execution_mode import ExecutionMode
from src.model.media_type import MediaType
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
    # asyncio queue's: https://stackoverflow.com/a/24704950/2402281
    input_queue: asyncio.Queue
    output_queue: asyncio.Queue

    def __init__(self, input_queue: asyncio.Queue, output_queue: asyncio.Queue,
                 mode: ExecutionMode = ExecutionMode.NORMAL):
        self._mode = mode
        self.output_queue = output_queue
        self.input_queue = input_queue
        self.reddit = None
        self.imgur = None

    def _init_reddit_client(self) -> None:
        if self.reddit is None:
            root_logger.info('Initializing async reddit client.')
            self.reddit: RedditClient = RedditClient()

    def _init_imgur_client(self) -> None:
        if self.imgur is None:
            root_logger.info('Initializing sync imgur client.')
            self.imgur: ImgurClient = ImgurClient(config.IMGUR_CLIENT_ID, config.IMGUR_CLIENT_SECRET)

    async def run(self, *args, **kwargs) -> None:
        self._init_reddit_client()
        root_logger.debug('Calling controller.run ...')
        await self.fetch()
        await self.work()
        await self.upload_and_answer()

    async def fetch(self) -> None:
        """Must not be called more than every 2 seconds to not violate reddit rate limits.
        """
        # todo custom logger
        self._init_reddit_client()
        root_logger.info('Fetching new messages...')
        try:
            await self._fill_task_queue_from_reddit()
        except Exception as err:
            log_broad_exception(err, logger=root_logger)

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
        _result: Result
        if self._mode == ExecutionMode.TEST:
            _result = self._read_result_from_output_queue(logger=upload_logger)
            if _result is None:  # fixme
                return
            filename = 'test.gif'  # fixme change extension by hand when in TEST mode
            with open(filename, mode='wb') as fp:
                # if _result.media_type == MediaType.GIF:
                #     # save GIF into named temp file for upload with deprecated imgur lib...
                #     _result.media_stream.save(fp=fp, format='GIF', save_all=True)
                # else:
                fp.write(_result.media_stream.getvalue())
            upload_logger.debug(f'Created file: {filename}')
            return
        self._init_imgur_client()  # make sure imgur client is connected
        self._init_reddit_client()  # make sure reddit client is connected
        _result = self._read_result_from_output_queue(logger=upload_logger)
        if _result is None:  # fixme
            upload_logger.warning('Received NoneType result.')
            return
        else:
            upload_logger.info(f'Uploading result: {_result}')
        upload_link = await self._upload_to_imgur(result=_result)
        await self._answer_in_reddit(message=_result.message, upload_link=upload_link)

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

    # noinspection PyMethodMayBeStatic
    def _exert_task(self, task: t.Task) -> Result:
        if task.is_state(TaskState.VALID):
            # _gif: GifImageFile
            cut_logger.info('Handling task...')
            try:
                result: Result = task.handle()
                return result
                # return Result(message=task.config.message, gif=_gif, gif_duration=_gif_duration)
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

    def _read_result_from_output_queue(self, logger) -> Optional[Result]:
        # todo custom logger
        try:
            logger.info('Attempting to immediately get task from output queue without blocking...')
            _result: Result = self.output_queue.get_nowait()
        except ValueError:
            logger.error(f'Queue is closed.')
        except asyncio.QueueEmpty:
            logger.warning(f'Queue is empty.')
            logger.debug(f'Output queue: {self.output_queue}')
        except Exception as err:
            log_broad_exception(err)
        else:
            return _result

    # @decorator.run_in_executor
    async def _upload_to_imgur(self, result: Result) -> str:
        # self.imgur
        # todo worth to have this async because of io
        # with NamedTemporaryFile(mode='wb', suffix='.gif') as fp:
        # save GIF into named temp file for upload with deprecated imgur lib...
        # result.gif.save(fp=fp, format='GIF', save_all=True, duration=result)
        # res = self.imgur.upload_from_path(path=fp.name, anon=False)
        anon = False
        if result.media_type == MediaType.GIF:
            payload = {'image': base64.b64encode(result.media_stream.getvalue()), 'type': 'base64'}
            anon = True
            # payload = {'image': result.media_stream}
        else:
            payload = {
                'type': 'file',
                'disable_audio': '0',
                'video': result.media_stream
            }
        res = self.imgur.upload(upload_payload=payload, anon=anon)
        upload_logger.debug(f'Upload to imgur: {res.get("link")}')
        # todo error handling with res
        return res.get('link')

    # @decorator.run_in_executor
    # noinspection PyMethodMayBeStatic
    async def _answer_in_reddit(self, message: Message, upload_link: str) -> None:
        # todo need a custom result data type to answer the message T_T
        # reply with link to the just cut gif and mark as unread
        issue_link = f'https://www.reddit.com/message/compose/?to=domac&subject={config.REDDIT_USERNAME}%20issue&message=' \
                     f'Add a link to the gif or comment in your message%2C I%27m not always sure which request is ' \
                     f'being reported. Thanks for helping me out! '
        bot_footer = f"---\n\n^(I am a bot.) [^(Report an issue)]({issue_link})"
        await message.reply(f'Here is your cut GIF: {upload_link}\n{bot_footer}')
        # m.mark_read()  # done
        upload_logger.info('Reddit reply sent!')
