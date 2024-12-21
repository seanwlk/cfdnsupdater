# cfdnsupdater
The main purpose of this script is to update IP records on cloudflare DNS

Optional
- Sends notification to a specific device via HomeAssistant
- Updates Atlas MongoDB access list with the new IP

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
