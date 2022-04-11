import logging
import sys

from typing import Union


# credits: https://stackoverflow.com/a/56944256/2402281
class ColorFormatter(logging.Formatter):
    default = '\x1b[39m'
    grey = '\x1b[38;20m'
    yellow = '\x1b[33;20m'
    red = '\x1b[31;20m'
    bold_red = '\x1b[31;1m'
    reset = '\x1b[0m'
    format = '{color}[%(asctime)-15s] [%(name)-12.12s] [%(levelname)-8s] --- %(message)s {reset} (%(filename)s:%(' \
             'lineno)d)'

    common_config = {
        'reset': reset,
    }

    FORMATS = {
        logging.DEBUG: format.format(color=default, **common_config),
        logging.INFO: format.format(color=grey, **common_config),
        logging.WARNING: format.format(color=yellow, **common_config),
        logging.ERROR: format.format(color=red, **common_config),
        logging.CRITICAL: format.format(color=bold_red, **common_config),
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


root_logger: logging.Logger
cut_logger: logging.Logger
upload_logger: logging.Logger


def setup_logger(level: Union[int, str] = logging.DEBUG):
    global root_logger, cut_logger, upload_logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(ColorFormatter())

    root_logger = logging.getLogger(name='gifCutterBot')
    cut_logger = logging.getLogger(name='CutWorker')
    upload_logger = logging.getLogger(name='UploadWorker')

    for logger in [root_logger, cut_logger, upload_logger]:
        logger.setLevel(level=level)
        logger.addHandler(handler)


setup_logger(level=logging.DEBUG)
