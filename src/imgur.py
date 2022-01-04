from imgurpython import ImgurClient

from config import IMGUR_CLIENT_ID
from config import IMGUR_CLIENT_SECRET


class ImgurHost:
    _client = None

    def __init__(self):
        client_id = IMGUR_CLIENT_ID
        client_secret = IMGUR_CLIENT_SECRET
        self._client = ImgurClient(client_id, client_secret)

    def upload(self, fp: str, **config):
        res = self._client.upload_from_path(fp, config=config, anon=False)
        return res
