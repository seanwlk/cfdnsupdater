#!/bin/bash

CRON_SCHEDULE=${CRON_FREQUENCY:-"*/30 * * * *"}

touch /app/dnsupdater.log

echo "$CRON_SCHEDULE python /app/dnsupdater.py >> /app/dnsupdater.log 2>&1" > /etc/crontabs/root

echo "Running initial DNS update..."
python /app/dnsupdater.py >> /app/dnsupdater.log 2>&1 &

echo "Starting cron daemon with schedule: $CRON_SCHEDULE"
crond -f -l 8 &

tail -f /app/dnsupdater.log