# syntax=docker/dockerfile:1
FROM python:3.9.9-slim
WORKDIR /code
RUN apt-get update && apt-get install -y ffmpeg
#COPY requirements.txt requirements.txt
COPY . .
RUN pip install -r requirements.txt
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH='.'
CMD ["python3", "src/main.py"]
