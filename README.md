# cfdnsupdater
The main purpose of this script is to update IP records on cloudflare DNS

Optional
- Sends notification to a specific device via HomeAssistant
- Sends notifications to a Telegram chat
- Updates Atlas MongoDB access list with the new IP

Notification channels are configured in `config.json`. Set `HASS.enabled` or
`Telegram.enabled` to `true` to use that channel. Telegram requires a bot token
and chat ID; disabled channels can keep their credentials in the config.

### Docker
You can run it as a docker container by building it and mounting your `config.json` file to `/app/config.json`

Build
```bash
docker build -t dnsupdater:latest .
```

Run
```bash
docker run --name DNSUpdater -it dnsupdater:latest \
  -e CRON_FREQUENCY='*/30 * * * *' \
  -e LOGLEVEL='INFO' \
  -v /my/path/to/config.json:/app/config.json
```
