import asyncio
import functools
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import Coroutine


# P = ParamSpec("P")
# R = TypeVar('R')
# POST_R = TypeVar('POST_R')
#
#
# def create_hook(
#         pre: Optional[Callable[[P], P]] = None, post: Optional[Callable[[R], POST_R]] = None
# ) -> Callable[[P], Union[R, POST_R]]:
#     def _decorate(f: Callable[[P], R]) -> Callable[[P], Union[R, POST_R]]:
#         @functools.wraps(f)
#         def wrapper(*args: P.args, **kwargs: P.kwargs):
#             if pre is not None:
#                 ret: R = f(pre(*args, **kwargs))
#             else:
#                 ret: R = f(*args, **kwargs)
#             if post is not None:
#                 return post(ret)
#             return ret
#         return wrapper
#     return _decorate


def run_in_executor(f) -> Callable[..., Coroutine[Any, Any, Awaitable]]:
    @functools.wraps(f)
    async def inner(*args: Any, **kwargs: Any) -> Awaitable:
        loop = asyncio.get_running_loop()
        return loop.run_in_executor(None, lambda: f(*args, **kwargs))

    return inner
