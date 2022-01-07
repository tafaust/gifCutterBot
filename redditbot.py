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
from src.gif_utilities import cut_gif as cut_gif_func
from src.logger import root


def run(reddit, imgur):
    # todo extend pattern
    pattern = re.compile(r'(s|start)=([\d]+) (e|end)=([\d]+)', re.IGNORECASE)
    params = {}
    inbox = reddit.inbox.unread(limit=None)
    for m in inbox:
        root.info(f'Received message: {m.body}')
        # todo queue and periodically work through queue
        # extract params
        matches = pattern.search(m.body)
        if matches is None:
            root.warn('Skipping message because no match was found.')
            m.mark_read()
            continue
        root.debug(f'Found pattern matches: {matches.groups()}')
        params['start'] = int(matches.group(2))
        params['end'] = int(matches.group(4))
        params['img'] = Image.open(requests.get(m.submission.url, stream=True).raw)
        # print(params)
        cut_gif, target_duration = cut_gif_func(**params)

        with NamedTemporaryFile(mode='wb', suffix='.gif') as gif:
            cut_gif[0].save(
                gif,
                save_all=True,
                append_images=cut_gif[1:],
                optimize=False,
                duration=target_duration,
                loop=0
            )
            root.info('Uploading to imgur...')
            res = imgur.upload_from_path(gif.name, anon=False)
            root.info('Upload finished!')
        # reply with link to the just cut gif and mark as unread
        issue_link = f'https://www.reddit.com/message/compose/?to=domac&subject={REDDIT_USERNAME}%20issue&message=' \
                     f'Add a link to the gif or comment in your message%2C I%27m not always sure which request is ' \
                     f'being reported. Thanks for helping me out! '
        bot_footer = f"---\n\n^(I am a bot.) [^(Report an issue)]({issue_link})"
        m.reply(f'Here is your cut GIF: {res.get("link")}\n{bot_footer}')
        m.mark_read()  # done
        root.info('Reddit reply sent!')


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
    root.info('Starting gifCutterBot...')
    reddit_instance = praw.Reddit(
        user_agent=USER_AGENT,
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        username=REDDIT_USERNAME,
        password=REDDIT_PASSWORD,
    )
    root.info('Reddit client connected!')
    imgur_instance = ImgurClient(IMGUR_CLIENT_ID, IMGUR_CLIENT_SECRET)
    root.info('Imgur client connected!')

    # run script every 10 seconds
    interval_seconds = 10
    it = IntervalTimer(interval=interval_seconds, worker_func=lambda: run(reddit=reddit_instance, imgur=imgur_instance))
    try:
        root.info(f'Running every {interval_seconds} seconds.')
        it.start()  # run indefinitely
    except (InterruptedError, KeyboardInterrupt):
        root.info('Periodic execution stopped.')
        it.stop()  # stop on ctrl+c or sigterm
