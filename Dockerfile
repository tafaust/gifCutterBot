# syntax=docker/dockerfile:1
FROM python:3.9.9-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /code
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .
CMD ["python3", "redditbot.py"]
