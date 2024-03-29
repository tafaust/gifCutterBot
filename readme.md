[![CodeQL](https://github.com/tahesse/gifCutterBot/actions/workflows/codeql-analysis.yml/badge.svg?branch=main)](https://github.com/tahesse/gifCutterBot/actions/workflows/codeql-analysis.yml)
[![Python application](https://github.com/tahesse/gifCutterBot/actions/workflows/python-app.yml/badge.svg?branch=main)](https://github.com/tahesse/gifCutterBot/actions/workflows/python-app.yml)
[![Docker Image CI](https://github.com/tahesse/gifCutterBot/actions/workflows/docker-image.yml/badge.svg?branch=main)](https://github.com/tahesse/gifCutterBot/actions/workflows/docker-image.yml)

# Reddit _gifcutterbot_ :clapper:

This reddit bot currently runs under [/u/gifcutterbot](https://www.reddit.com/user/gifcutterbot/). 

## Purpose of this bot :robot:

You are looking at GIFs and you come across a GIF for which you really only want to see one cut scene from.
Linking this bot and with your desired start and end time in milliseconds, this bot will provide you with an
imgur link to your cut scene GIF.

## Usage :diamond_shape_with_a_dot_inside:
To cut the GIF or video of a post, simply add your comment

> /u/gifcutterbot start=[time-in-milliseconds] end=[time-in-milliseconds]

For example like this:

> /u/gifcutterbot start=3500 end=9200

# Development and Contribution :call_me_hand:

Please contribute to this bot and send descriptive pull requests! 

If you want to development work on the bot, make sure to have a `.env` file sourced with the keys:
```
REDDIT_USERNAME=
REDDIT_PASSWORD=
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=

IMGUR_CLIENT_ID=
IMGUR_CLIENT_SECRET=
```
whereas you have to create reddit and imgur test accounts with applications yourself to fill in the values.

Dependencies can be installed with `pip install -r requirements.txt` from your project root directory.

After that, you can run the bot from the project root directory using the command
```shell
PYTHONPATH=. python src/main.py
```

## Testing :test_tube:

If you want to run the tests, in your project root directory, type
```shell
PYTHONPATH=. pytest
```
to run the pytest suite.

All tests are located in the `tests` directory in the project root directory.
