from os import getenv

from src.util.logger import root_logger

REDDIT_USERNAME = getenv('REDDIT_USERNAME')
REDDIT_PASSWORD = getenv('REDDIT_PASSWORD')
REDDIT_CLIENT_ID = getenv('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = getenv('REDDIT_CLIENT_SECRET')

with open('VERSION', 'r') as f:
    version = f.readline().strip()
    root_logger.debug(f'Load version string "{version}" for User-Agent')
    USER_AGENT = f'web:gifcutterbot:v{version} (by /u/domac)'

IMGUR_CLIENT_ID = getenv('IMGUR_CLIENT_ID')
IMGUR_CLIENT_SECRET = getenv('IMGUR_CLIENT_SECRET')
