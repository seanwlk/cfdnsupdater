import logging
import requests
import json
import sys

logger = logging.getLogger(__name__)
logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')

class updater:
  def __init__(self,conf):
    self.mail = conf['mail']
    self.authToken = conf['authToken']
    self.zoneID = conf['zoneID']
    self.identifier = conf['identifier']
    self.recordName = conf['dnsname']
    self.recordType = conf['dnstype']
    self.hass = conf['HASS']
  def sendHASSnotification(self, title, message):
    headers = {
      "Authorization": f"Bearer {self.hass['token']}",
      "Content-Type": "application/json"
    }
    req = requests.post(f"http://{self.hass['host']}:8123/api/services/notify/{self.hass['device']}", headers=headers, json={"title": title, "message":message})
    return None
  def getIP(self):
    try:
      myIP = requests.get("https://ipinfo.io").json()['ip']
    except:
      myIP = False
    return myIP
  def listCFIdentifiersByZoneID(self, zoneID):
    req = requests.get(f"https://api.cloudflare.com/client/v4/zones/{zoneID}/dns_records",headers=headers).json()
    return req
  def updateCFIP(self, ip):
    headers = {
      'X-Auth-Email' : self.mail,
      'Authorization' : f"Bearer {self.authToken}",
      'Content-Type' : 'application/json'
    }
    data = {
      'type' : self.recordType,
      'name' : self.recordName,
      'content' : ip,
      'ttl' : 1,
      'proxied' : True
    }
    req = requests.put(f"https://api.cloudflare.com/client/v4/zones/{self.zoneID}/dns_records/{self.identifier}",headers=headers,data=json.dumps(data)).json()
    if "success" in req:
      return True
    logger.error(f"Cannot update IP on cloudflare: {req['error']}")
    return False
  def saveIPtoFile(self,ip):
    with open('current_ip','w') as f:
      f.write(ip)
    return None
  def readIPfromFile(self):
    try:
      with open('current_ip','r') as f:
        c = f.read()
    except:
      with open('current_ip', 'w') as file:
        c = 'NO_IP'
    return str(c)


mgr = updater(json.load(open('config.json')))

current_ip = mgr.readIPfromFile()
ip = mgr.getIP()

if not ip:
  logger.error("Cannot retrieve current IP address")
  sys.exit()
if ip != current_ip:
  logger.info(f"IP changed from {current_ip} to {ip}")
  mgr.sendHASSnotification("Home IP Changed", f"{current_ip} to {ip}")
  cf = mgr.updateCFIP(ip)
  if cf:
    mgr.saveIPtoFile(ip)
else:
  logger.debug("IP did not change")
  sys.exit()
