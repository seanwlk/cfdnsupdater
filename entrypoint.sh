#!/bin/bash

CRON_SCHEDULE=${CRON_FREQUENCY:-"*/30 * * * *"}

echo "$CRON_SCHEDULE python /app/dnsupdater.py >> /proc/1/fd/1 2>&1" > /etc/crontabs/root

touch /var/log/cron.log
crond -f -L /var/log/cron.log &

# Run at startup
python /app/dnsupdater.py

tail -f /var/log/cron.log