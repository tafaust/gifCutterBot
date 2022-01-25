import asyncio
from typing import Callable

from src import timer
from src.execution.controller import AioController
from src.model.execution_mode import ExecutionMode


def start_aio_timer(
        interval: int, callback: Callable, sleep_first: bool = False, loop: asyncio.AbstractEventLoop = None
):
    _timer = timer.PeriodicAsyncIOTimer(interval=interval, function=callback, sleep_first=sleep_first, loop=loop)
    try:
        _timer.run()
        if loop is None:
            _timer.start_loop()
    except:
        _timer.cancel()
        _timer.stop_loop()


if __name__ == '__main__':
    _mode: ExecutionMode = ExecutionMode.NORMAL
    # controller: dictates the general workflow; individual steps can be called though
    _controller: AioController = AioController(input_queue=asyncio.Queue(), output_queue=asyncio.Queue(), mode=_mode)

    _loop = asyncio.new_event_loop()
    start_aio_timer(interval=10, callback=_controller.fetch, loop=_loop)
    start_aio_timer(interval=5, callback=_controller.work, sleep_first=True, loop=_loop)
    start_aio_timer(interval=10, callback=_controller.upload_and_answer, sleep_first=True, loop=_loop)
    _loop.run_forever()
