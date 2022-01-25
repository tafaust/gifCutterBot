from os import getenv
from typing import AsyncIterator
from typing import Iterator
from typing import Union

import asyncpraw
from asyncpraw.models import Comment
from asyncpraw.models import Message

from src.util.config import REDDIT_CLIENT_ID
from src.util.config import REDDIT_CLIENT_SECRET
from src.util.config import REDDIT_PASSWORD
from src.util.config import REDDIT_USERNAME
from src.util.config import USER_AGENT


class RedditClient:
    def __init__(self):
        self._instance = asyncpraw.Reddit(
                user_agent=USER_AGENT,
                client_id=REDDIT_CLIENT_ID,
                client_secret=REDDIT_CLIENT_SECRET,
                username=REDDIT_USERNAME,
                password=REDDIT_PASSWORD,
                ratelimit_seconds='60000',
        )

    async def has_new_message(self) -> bool:
        """Checks whether a new message is in the inbox.

        Returns:
            True if there are messages in the inbox, False otherwise.
        """
        inbox = self._instance.inbox.unread(limit=None)
        # return any([True async for _ in inbox])
        try:
            await inbox.__anext__()
            return True
        except StopAsyncIteration:
            return False

    def fetch_new_messages(self) -> AsyncIterator[Union[Comment, Message]]:
        return self._instance.inbox.unread(limit=None)
