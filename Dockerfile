FROM python:3.12-alpine

# Config
ENV PYTHONUNBUFFERED=1
ENV CRON_FREQUENCY="*/30 * * * *"
ENV LOGLEVEL="INFO"

LABEL name="dnsupdater"
LABEL description="DNS Updater for Cloudflare"

RUN apk update && \
    apk add --no-cache \
    bash \
    curl \
    dcron \
    && pip install requests

RUN mkdir -p /app

COPY dnsupdater.py /app/dnsupdater.py
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Run the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]