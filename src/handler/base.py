from __future__ import annotations

import abc
from io import BytesIO

import src.execution.task as task_pkg
import src.model.result as result_pkg


class BaseCutHandler(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def cut(self, stream: BytesIO, config: task_pkg.TaskConfig) -> result_pkg.Result: ...
