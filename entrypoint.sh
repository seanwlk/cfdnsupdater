#!/bin/bash

CRON_SCHEDULE=${CRON_FREQUENCY:-"*/30 * * * *"}

echo "$CRON_SCHEDULE python /app/dnsupdater.py > /proc/1/fd/1 2>&1" > /etc/crontabs/root

echo "Running initial DNS update..."
python /app/dnsupdater.py > /proc/1/fd/1 2>&1 &

echo "Starting cron daemon with schedule: $CRON_SCHEDULE"
crond -f -l 8