import logging
from dataclasses import dataclass, asdict
from typing import Union, Any

import requests

# import aiohttp
# from aiohttp import ClientResponse


@dataclass
class UploadPayload:
    """
    Attributes:
        image           A binary file, base64 data, or a URL for an image. (up to 10MB)
        video           A binary file (up to 200MB)
        album           The id of the album you want to add the image to. For anonymous albums, album should be the deletehash that is returned at creation
        type            The type of the file that's being sent; file, base64 or URL
        name            The name of the file, this is automatically detected if uploading a file with a POST and multipart / form-data
        title           The title of the image
        description     The description of the image
        disable_audio   Will remove the audio track from a video file
    """
    image: Union[bytes, str]
    video: bytes
    album: str
    type: str
    name: str
    title: str
    description: str
    disable_audio: int


@dataclass
class ImgurResponseData:
    id: str
    name: Any
    description: Any
    datetime: Any
    type: Any
    animated: Any
    width: Any
    height: Any
    size: Any
    views: Any
    bandwidth: Any
    vote: Any
    favorite: Any
    nsfw: Any
    section: Any
    account_url: Any
    account_id: Any
    is_ad: Any
    in_most_viral: Any
    has_sound: Any
    tags: Any
    ad_type: Any
    ad_url: Any
    edited: Any
    in_gallery: Any
    deletehash: Any
    name: Any
    link: Any


@dataclass
class ImgurResponse:
    success: bool
    status: int
    data: ImgurResponseData


class ImgurClient:
    api_version: int = 3
    api_url: str

    def __init__(self, client_id, client_secret=None):
        self.logger = logging.getLogger(name='ImgurClient')
        self.client_id = client_id
        self.client_secret = client_secret
        self.headers = {
            'Authorization': f'Client-ID {self.client_id}'
        }
        self.api_url = f'https://api.imgur.com/{self.api_version}'
        self._default_request_params = {
            'raise_for_status': False,
        }

    def __del__(self):
        del self.client_id
        del self.client_secret

    # account

    async def authenticate(self):
        pass

    # image

    def upload(self, upload_payload: dict, anon: bool = False) -> ImgurResponseData:
        # response: ClientResponse
        # imgur_response: ImgurResponse
        url = f'{self.api_url}/upload'
        data = upload_payload
        video = data.pop('video', None)
        _post_params = {
            # **self._default_request_params,
            'url': url,
            'headers': {
                **(self.headers if not anon else {}),
            },
            'data': data,
        }
        if video is not None:
            _post_params['files'] = [('video', video)]
        # async with aiohttp.ClientSession() as session:
        #     async with session.post(**_post_params) as response:
        with requests.Session() as s:
            with s.post(**_post_params) as response:
                imgur_response = response.json()
                return imgur_response['data']
