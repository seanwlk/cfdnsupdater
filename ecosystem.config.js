module.exports = {
  apps : [{
    name   : "DNS-Updater",
    namespace : "task",
    script : "python3",
    watch: false,
    instances: 1,
    args : "dnsupdater.py",
    cron_restart : "*/30 * * * *",
    autorestart : false
  }]
}
