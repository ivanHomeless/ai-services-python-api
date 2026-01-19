FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y wget bzip2 xz-utils ca-certificates && \
    wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz && \
    tar -xvf ffmpeg-release-amd64-static.tar.xz && \
    mv ffmpeg-*-static/ffmpeg /usr/bin/ffmpeg && \
    mv ffmpeg-*-static/ffprobe /usr/bin/ffprobe && \
    chmod +x /usr/bin/ffmpeg /usr/bin/ffprobe && \
    rm -rf ffmpeg-release-amd64-static*

COPY ./app ./app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]