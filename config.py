from os import getenv

REDDIT_USERNAME = getenv('REDDIT_USERNAME')
REDDIT_PASSWORD = getenv('REDDIT_PASSWORD')
REDDIT_CLIENT_ID = getenv('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = getenv('REDDIT_CLIENT_SECRET')

with open('VERSION', 'r') as f:
    USER_AGENT = f'web:gifcutterbot:v{f.readline()} (by /u/domac)'

IMGUR_CLIENT_ID = getenv('IMGUR_CLIENT_ID')
IMGUR_CLIENT_SECRET = getenv('IMGUR_CLIENT_SECRET')
