import re
from tempfile import NamedTemporaryFile

import praw
import requests
from PIL import Image

from config import REDDIT_CLIENT_ID
from config import REDDIT_CLIENT_SECRET
from config import REDDIT_PASSWORD
from config import REDDIT_USERNAME
from config import USER_AGENT
from src.gif_utilities import cut_gif
from src.imgur import ImgurHost

if __name__ == '__main__':
    # todo refactor reddithost into its own class
    reddit = praw.Reddit(
        user_agent=USER_AGENT,
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        username=REDDIT_USERNAME,
        password=REDDIT_PASSWORD,
    )

    imgur = ImgurHost()

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
            res = imgur.upload(gif.name)
        # reply with link to the just cut gif and mark as unread
        m.reply(f'Here is your cut GIF: {res.get("link")}')
        m.mark_read()  # done
