FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 RADIO_DATA=/data
RUN apt-get update && apt-get install -y --no-install-recommends \
    fluidsynth timgm6mb-soundfont ffmpeg liquidsoap icecast2 curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --create-home radio \
    && mkdir /data && chown radio:radio /data
WORKDIR /app
COPY radio /app/radio
COPY deploy /app/deploy
USER radio
CMD ["python", "-m", "radio", "composer"]
