# syntax=docker/dockerfile:1
FROM python:3.9.9-slim
WORKDIR /code
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .
CMD ['python', 'redditbot.py']
