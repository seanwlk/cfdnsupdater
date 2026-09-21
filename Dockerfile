FROM python:3.14-alpine

# Config
ENV PYTHONUNBUFFERED=1
ENV CRON_FREQUENCY="*/30 * * * *"
ENV LOGLEVEL="INFO"
ENV ENV="/root/.ashrc"

LABEL name="dnsupdater"
LABEL description="DNS Updater for Cloudflare"

RUN apk update && \
    apk add --no-cache \
    bash \
    curl \
    dcron \
    && pip install requests

RUN mkdir -p /app

# 'rundns' alias to run from docker cli
RUN echo 'alias rundns="python /app/dnsupdater.py"' >> /root/.bashrc && \
  echo 'alias rundns="python /app/dnsupdater.py"' >> /root/.ashrc

COPY dnsupdater.py /app/dnsupdater.py
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Run the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]