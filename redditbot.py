import re
from tempfile import NamedTemporaryFile
from threading import Thread, Event
from time import sleep  # blocks the current thread synchronously

import praw
import requests
from PIL import Image
from imgurpython import ImgurClient

from config import IMGUR_CLIENT_ID
from config import IMGUR_CLIENT_SECRET
from config import REDDIT_CLIENT_ID
from config import REDDIT_CLIENT_SECRET
from config import REDDIT_PASSWORD
from config import REDDIT_USERNAME
from config import USER_AGENT
from src.gif_utilities import cut_gif


def run(reddit, imgur):
    # todo extend pattern
    pattern = re.compile(r'start=([\d]+) end=([\d]+)')
    params = {}
    # todo infinite loop or cronjob
    for m in reddit.inbox.unread(limit=None):
        # todo queue and periodically work through queue
        # extract params
        matches = pattern.search(m.body)
        params['start'] = int(matches.group(1))
        params['end'] = int(matches.group(2))
        params['img'] = Image.open(requests.get(m.submission.url, stream=True).raw)
        print(params)
        cutGif, target_duration = cut_gif(**params)

        with NamedTemporaryFile(mode='wb', suffix='.gif') as gif:
            cutGif[0].save(
                gif,
                save_all=True,
                append_images=cutGif[1:],
                optimize=False,
                duration=target_duration,
                loop=0
            )
            res = imgur.upload_from_path(gif.name, anon=False)
        # reply with link to the just cut gif and mark as unread
        m.reply(f'Here is your cut GIF: {res.get("link")}')
        m.mark_read()  # done


# Credits: https://stackoverflow.com/a/22702362/2402281
class StoppableThread(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.stop_event = Event()

    def stop(self):
        if self.isAlive():
            # set event to signal thread to terminate
            self.stop_event.set()
            # block calling thread until thread really has terminated
            self.join()


class IntervalTimer(StoppableThread):
    def __init__(self, interval, worker_func):
        super().__init__()
        self._interval = interval
        self._worker_func = worker_func

    def run(self):
        while not self.stop_event.is_set():
            self._worker_func()
            sleep(self._interval)


if __name__ == '__main__':
    reddit_instance = praw.Reddit(
        user_agent=USER_AGENT,
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        username=REDDIT_USERNAME,
        password=REDDIT_PASSWORD,
    )
    imgur_instance = ImgurClient(IMGUR_CLIENT_ID, IMGUR_CLIENT_SECRET)

    # run script every 3 seconds
    it = IntervalTimer(3, lambda: run(reddit=reddit_instance, imgur=imgur_instance))
    try:
        it.start()  # run indefinitely
    except (InterruptedError, KeyboardInterrupt):
        it.stop()  # stop on ctrl+c or sigterm
