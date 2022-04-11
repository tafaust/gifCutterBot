import asyncio
from typing import Callable

from src.util.logger import root_logger


class AsyncIOTimer(object):
    def __init__(
            self, timeout: int, function: Callable, loop: asyncio.AbstractEventLoop = None, args=None,
            kwargs=None
    ):
        self._task = None
        self._timeout = timeout
        self._function = function
        self.args = [] if args is None else args
        self.kwargs = {} if kwargs is None else kwargs
        self._event_loop = asyncio.new_event_loop() if loop is None else loop

    def start_loop(self):
        self._event_loop.run_forever()

    def stop_loop(self):
        self._event_loop.stop()

    async def _job(self):
        await asyncio.sleep(self._timeout)
        await self._function()

    def run(self):
        if self._task is None:
            self._task = self._event_loop.create_task(self._job())
        else:
            root_logger.error('Task is already running!')

    def cancel(self):
        if self._task is None:
            root_logger.error('No task is running!')
            return
        self._task.cancel()
        self._task = None


class PeriodicAsyncIOTimer(AsyncIOTimer):
    def __init__(
            self, interval: int, function: Callable, *, loop: asyncio.AbstractEventLoop = None, sleep_first=False,
            args=None, kwargs=None
    ):
        super(PeriodicAsyncIOTimer, self).__init__(
                timeout=interval, function=function, loop=loop, args=args, kwargs=kwargs
        )
        self._sleep_first = sleep_first
        self._canceled = False

    async def __job_sleep_after(self):
        await self._function()
        await asyncio.sleep(self._timeout)

    async def _job(self):
        _callback = super(PeriodicAsyncIOTimer, self)._job if self._sleep_first else self.__job_sleep_after
        while not self._canceled:
            try:
                await _callback()
            except Exception as err:
                root_logger.error(f'Caught exception ({type(err).__name__}) in timer: {err}')
                await asyncio.sleep(self._timeout)  # sleep after an error was received!

    def run(self):
        if self._task is None:
            self._task = self._event_loop.create_task(self._job())
        else:
            root_logger.error('Task is already running!')

    def cancel(self):
        super(PeriodicAsyncIOTimer, self).cancel()
        self._canceled = True
