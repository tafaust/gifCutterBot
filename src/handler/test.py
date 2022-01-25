from __future__ import annotations

from io import BytesIO

from src.execution import task
from src.handler.base import BaseCutHandler
from src.util.logger import root_logger


class TestCutHandler(BaseCutHandler):
    def cut(self, stream: BytesIO, config: task.TaskConfig):
        root_logger.debug(stream.getvalue().decode('utf-8'))
