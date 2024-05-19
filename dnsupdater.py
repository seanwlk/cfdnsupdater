import logging
import argparse
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
    self.dnsList = conf['DNS']
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
    headers = {
      'X-Auth-Email' : self.mail,
      'Authorization' : f"Bearer {self.authToken}",
      'Content-Type' : 'application/json'
    }
    req = requests.get(f"https://api.cloudflare.com/client/v4/zones/{zoneID}/dns_records",headers=headers).json()
    return req
  def updateCFIP(self, ip):
    headers = {
      'X-Auth-Email' : self.mail,
      'Authorization' : f"Bearer {self.authToken}",
      'Content-Type' : 'application/json'
    }
    for dns in self.dnsList:
      data = {
        'type' : dns['dnstype'],
        'name' : dns['dnsname'],
        'content' : ip,
        'ttl' : 1,
        'proxied' : dns['proxied']
      }
      req = requests.put(f"https://api.cloudflare.com/client/v4/zones/{self.zoneID}/dns_records/{dns['identifier']}",headers=headers,data=json.dumps(data)).json()
      if not req['success']:
        logger.error(f"Cannot update IP on cloudflare for dns {dns['name']}: {req['error']}")
    return True
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

def runDNSUpdate(m):
  current_ip = m.readIPfromFile()
  ip = m.getIP()

  if not ip:
    logger.error("Cannot retrieve current IP address")
    sys.exit()
  if ip != current_ip:
    logger.info(f"IP changed from {current_ip} to {ip}")
    m.sendHASSnotification("Home IP Changed", f"{current_ip} to {ip}")
    cf = m.updateCFIP(ip)
    if cf:
      m.saveIPtoFile(ip)
  else:
    logger.debug("IP did not change")
    sys.exit()

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="CloudFlare DNS Updater")
  parser.add_argument('--ldns', action='store_true', help='List account DNS and identifiers')
  args = parser.parse_args()
  mgr = updater(json.load(open('config.json')))
  if args.ldns:
    data = mgr.listCFIdentifiersByZoneID(mgr.zoneID)
    if not data['success']:
      logger.error("Cannot retreive DNS list: "+str(data['errors']))
      sys.exit()
    o = "Identifier\t\t\t\tType\tProxied\tName\n"
    for d in data['result']:
      o+=f"{d['id']}\t{d['type']}\t{d['proxied']}\t{d['name'].replace('.'+d['zone_name'],'')}\n"
    print(o)
    sys.exit()
  else:  
    runDNSUpdate(mgr)
