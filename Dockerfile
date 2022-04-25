FROM python:3.9.12-slim

RUN groupadd --gid 1000 cutterbot \
  && useradd --uid 1000 --gid cutterbot --shell /bin/bash --create-home cutterbot
USER cutterbot:cutterbot
WORKDIR /home/cutterbot
COPY . .
#COPY requirements.txt requirements.txt
RUN apt-get update && apt-get install -y ffmpeg && pip install -r requirements.txt
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH='.'
CMD ["python3", "src/main.py"]
