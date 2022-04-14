""" Copyright start
  Copyright (C) 2008 - 2022 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """

import requests, datetime, time
from connectors.core.connector import get_logger, ConnectorError

try:
    from integrations.crudhub import trigger_ingest_playbook
except:
    # ignore. lower FSR version
    pass

logger = get_logger('ssl-blacklist-feed')

errors = {
    400: 'Bad/Invalid Request',
    401: 'Unauthorized: Invalid credentials provided failed to authorize',
    403: 'Access Denied',
    404: 'Not Found',
    500: 'Internal Server Error'
}

SERVICE = {
    "abuse.ch SSLBL Botnet C2 IP Blacklist (CSV)": "https://sslbl.abuse.ch/blacklist/sslipblacklist.csv",
    "abuse.ch SSLBL Botnet C2 IP Blacklist (CSV) - Aggressive": "https://sslbl.abuse.ch/blacklist/sslipblacklist_aggressive.csv"
}


class SSLBlacklistFeed(object):
    def __init__(self, config, *args, **kwargs):
        self.url = SERVICE.get(config.get('service'))
        self.sslVerify = config.get('verify_ssl')

    def make_rest_call(self, url, method):
        try:
            url = self.url
            response = requests.request(method, url, verify=self.sslVerify)
            if response.ok or response.status_code == 204:
                logger.info('Successfully got response for url {0}'.format(url))
                if 'json' in str(response.headers):
                    return response.json()
                else:
                    return response.content
            elif response.status_code == 404:
                return {'blocklist_ips': []}
            else:
                logger.error("{0}".format(errors.get(response.status_code, '')))
                raise ConnectorError("{0}".format(errors.get(response.status_code, response.text)))
        except requests.exceptions.SSLError:
            raise ConnectorError('SSL certificate validation failed')
        except requests.exceptions.ConnectTimeout:
            raise ConnectorError('The request timed out while trying to connect to the server')
        except requests.exceptions.ReadTimeout:
            raise ConnectorError(
                'The server did not send any data in the allotted amount of time')
        except requests.exceptions.ConnectionError:
            raise ConnectorError('Invalid endpoint or credentials')
        except Exception as err:
            raise ConnectorError(str(err))


def convert_datetime_to_epoch(date_time):
    d1 = time.strptime(date_time, "%Y-%m-%dT%H:%M:%S.%fZ")
    epoch = datetime.datetime.fromtimestamp(time.mktime(d1)).strftime('%s')
    return epoch


def fetch_indicators(config, params, **kwargs):
    sf = SSLBlacklistFeed(config)
    endpoint = ""
    ip_blacklist_list = []
    response = sf.make_rest_call(endpoint, 'GET')
    if response:
        ip_blacklist = str(response).split("\\r\\n")
        extract_last_updated = ip_blacklist[2].split(" ")
        last_updated = convert_datetime_to_epoch(extract_last_updated[3] + 'T' + extract_last_updated[4] + '.000Z')
        for ip in ip_blacklist[9:-1]:
            ip_data = ip.split(",")
            ip_blacklist_list.append({
                'ip': ip_data[1],
                'destination_port': ip_data[2],
                'first_seen': convert_datetime_to_epoch(ip_data[0].replace(" ", "T") + '.000Z'),
                'last_updated': last_updated
            })
        return ip_blacklist_list


def _check_health(config):
    try:
        sf = SSLBlacklistFeed(config)
        return True
    except Exception as err:
        raise ConnectorError('Invalid URL or Credentials')


operations = {
    'fetch_indicators': fetch_indicators
}
