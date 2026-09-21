import os
import logging
import argparse
import requests
import json
import sys
import time
from pathlib import Path
from requests.auth import HTTPDigestAuth
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log_level = getattr(logging, os.getenv("LOGLEVEL", "INFO"), logging.INFO)
log_file = Path(__file__).parent / "dnsupdater.log"

logging.basicConfig(
  level=log_level, 
  handlers=[logging.FileHandler(log_file, encoding='utf-8')], 
  format='%(asctime)s %(levelname)-8s %(message)s', 
  datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def retry_with_backoff(max_retries=5, initial_backoff=5):
  """
  Decorator for exponential backoff retries.
  Wait times double with each failure.
  """
  def decorator(func):
    def wrapper(*args, **kwargs):
      retries = 0
      while True:
        try:
          return func(*args, **kwargs)
        except requests.exceptions.RequestException as e:
          retries += 1
          if retries > max_retries:
            logger.error(f"Max retries reached for {func.__name__}. Last error: {e}")
            return False
          wait_time = initial_backoff * (2 ** (retries - 1))
          logger.warning(f"Error in {func.__name__}: {e}. Retrying in {wait_time}s (Attempt {retries}/{max_retries})...")
          time.sleep(wait_time)
    return wrapper
  return decorator


class Updater:
  def __init__(self, conf):
    self.mail = conf.get('mail', '')
    self.authToken = conf.get('authToken', '')
    self.zoneID = conf.get('zoneID', '')
    self.dnsList = conf.get('DNS', [])
    self.hass = conf.get('HASS', {})
    self.atlasMongo = conf.get('AtlasMongo', {})
    self.ip_file = Path(__file__).parent / 'current_ip'

    self.session = requests.Session()
    retry = Retry(
      total=3,
      backoff_factor=1,
      status_forcelist=[429, 500, 502, 503, 504],
      allowed_methods=["HEAD", "GET", "PUT", "POST", "DELETE", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    self.session.mount("http://", adapter)
    self.session.mount("https://", adapter)
    self.timeout = 15

  @retry_with_backoff(max_retries=6, initial_backoff=15)
  def send_hass_notification(self, title, message):
    if not self.hass.get('host'):
      return False
      
    headers = {
      "Authorization": f"Bearer {self.hass.get('token')}",
      "Content-Type": "application/json"
    }
    url = f"http://{self.hass['host']}:8123/api/services/notify/{self.hass['device']}"
    logger.info(f"Sending HASS notification to device {self.hass['device']} at {self.hass['host']}")
    
    response = self.session.post(
      url, 
      headers=headers, 
      json={"title": title, "message": message}, 
      timeout=self.timeout
    )
    response.raise_for_status()
    logger.info("HASS notification sent successfully.")
    return True

  @retry_with_backoff(max_retries=5, initial_backoff=5)
  def get_ip(self):
    response = self.session.get("https://ipinfo.io", timeout=self.timeout)
    response.raise_for_status()
    return response.json()['ip']

  def list_cf_identifiers_by_zone_id(self, zone_id):
    headers = {
      'X-Auth-Email': self.mail,
      'Authorization': f"Bearer {self.authToken}",
      'Content-Type': 'application/json'
    }
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
    response = self.session.get(url, headers=headers, timeout=self.timeout)
    response.raise_for_status()
    return response.json()

  def update_cf_ip(self, ip):
    headers = {
      'X-Auth-Email': self.mail,
      'Authorization': f"Bearer {self.authToken}",
      'Content-Type': 'application/json'
    }
    success = True
    for dns in self.dnsList:
      data = {
        'type': dns.get('dnstype', 'A'),
        'name': dns.get('dnsname'),
        'content': ip,
        'ttl': 1,
        'proxied': dns.get('proxied', True)
      }
      url = f"https://api.cloudflare.com/client/v4/zones/{self.zoneID}/dns_records/{dns.get('identifier')}"
      try:
        response = self.session.put(url, headers=headers, json=data, timeout=self.timeout)
        response.raise_for_status()
        req_data = response.json()
        if not req_data.get('success'):
          logger.error(f"Cloudflare update failed for {dns.get('dnsname')}: {req_data.get('errors')}")
          success = False
        else:
          logger.info(f"Cloudflare IP updated for {dns.get('dnsname')}")
      except requests.exceptions.RequestException as e:
        logger.error(f"Network error updating Cloudflare for {dns.get('dnsname')}: {e}")
        success = False
    return success

  def update_atlas_mongo_ip(self, new_ip, old_ip):
    project_id = self.atlasMongo.get('projectId')
    if not project_id:
      return False

    headers = {"Accept": "application/vnd.atlas.2024-05-30+json"}
    auth = HTTPDigestAuth(self.atlasMongo.get('publicKey'), self.atlasMongo.get('privateKey'))
    base_url = f"https://cloud.mongodb.com/api/atlas/v2/groups/{project_id}/accessList"

    try:
      response = self.session.get(base_url, auth=auth, headers=headers, timeout=self.timeout)
      response.raise_for_status()
      access_list = response.json().get('results', [])

      entry_id = None
      ip_already_exists = False

      for entry in access_list:
        if entry.get('ipAddress') == old_ip:
          entry_id = entry.get('groupId')
        elif entry.get('ipAddress') == new_ip:
          ip_already_exists = True
          logger.debug("New IP already registered in Atlas Access List")

      if entry_id and old_ip != 'NO_IP':
        delete_url = f"https://cloud.mongodb.com/api/atlas/v2/groups/{entry_id}/accessList/{old_ip}"
        del_res = self.session.delete(delete_url, auth=auth, headers=headers, timeout=self.timeout)
        del_res.raise_for_status()
        logger.info(f"Removed old IP {old_ip} from Atlas Access List.")

      if not ip_already_exists:
        new_entry = {
          "ipAddress": new_ip,
          "comment": self.atlasMongo.get('entryComment', 'Home Dynamic IP')
        }
        post_res = self.session.post(base_url, auth=auth, headers=headers, json=[new_entry], timeout=self.timeout)
        post_res.raise_for_status()
        logger.info(f"Added new IP {new_ip} to Atlas Access List.")
        
    except requests.exceptions.RequestException as e:
      logger.error(f"Failed to update Atlas Mongo IP: {e}")
      return False
      
    return True

  def save_ip_to_file(self, ip):
    try:
      self.ip_file.write_text(ip)
    except IOError as e:
      logger.error(f"Failed to write IP to file: {e}")

  def read_ip_from_file(self):
    try:
      return self.ip_file.read_text().strip()
    except FileNotFoundError:
      return 'NO_IP'
    except IOError as e:
      logger.error(f"Failed to read IP from file: {e}")
      return 'NO_IP'


def run_dns_update(mgr):
  current_ip = mgr.read_ip_from_file()
  ip = mgr.get_ip()

  if not ip:
    logger.error("Cannot retrieve current IP address after retries. Exiting.")
    sys.exit(1)

  if ip != current_ip:
    logger.info(f"IP changed from {current_ip} to {ip}")
    
    cf_success = mgr.update_cf_ip(ip)
    mgr.update_atlas_mongo_ip(ip, current_ip)
    mgr.send_hass_notification("Home IP Changed", f"{current_ip} to {ip}")
    
    if cf_success:
      mgr.save_ip_to_file(ip)
  else:
    logger.debug("IP did not change")
    sys.exit(0)


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="CloudFlare DNS Updater")
  parser.add_argument('--ldns', action='store_true', help='List account DNS and identifiers')
  args = parser.parse_args()

  config_path = Path(__file__).parent / 'config.json'
  try:
    with open(config_path, 'r') as f:
      config_data = json.load(f)
  except (FileNotFoundError, json.JSONDecodeError) as e:
    logger.error(f"Failed to load configuration from {config_path}: {e}")
    sys.exit(1)

  mgr = Updater(config_data)

  if args.ldns:
    try:
      data = mgr.list_cf_identifiers_by_zone_id(mgr.zoneID)
      if not data.get('success'):
        logger.error("Cannot retrieve DNS list: " + str(data.get('errors')))
        sys.exit(1)
        
      print("Identifier\t\t\t\tType\tProxied\tName")
      for d in data.get('result', []):
        zone_suffix = f".{d.get('zone_name')}"
        name = d.get('name', '').replace(zone_suffix, '')
        print(f"{d.get('id')}\t{d.get('type')}\t{d.get('proxied')}\t{name}")
      sys.exit(0)
    except requests.exceptions.RequestException as e:
      logger.error(f"API Error listing identifiers: {e}")
      sys.exit(1)
  else:
    run_dns_update(mgr)