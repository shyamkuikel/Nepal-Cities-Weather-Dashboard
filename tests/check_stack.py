"""Integration check for a running local Compose stack (used in CI)."""
import base64
import json
import os
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def grafana(path):
    credentials = (os.environ['GRAFANA_ADMIN_USER'] + ':' + os.environ['GRAFANA_ADMIN_PASSWORD']).encode()
    request = Request('http://127.0.0.1:3000' + path,
                      headers={'Authorization': 'Basic ' + base64.b64encode(credentials).decode()})
    with urlopen(request, timeout=5) as response:
        return json.load(response)


def check():
    deadline = time.monotonic() + 90
    while True:
        try:
            assert grafana('/api/health')['database'] == 'ok'
            dashboard = grafana('/api/dashboards/uid/nepal-cities-weather')['dashboard']
            assert dashboard['timezone'] == 'Asia/Kathmandu'
            assert len(dashboard['panels']) == 41
            datasource = grafana('/api/datasources/uid/weather-prometheus')
            assert datasource['url'] == 'http://prometheus:9090'
            break
        except (OSError, HTTPError, URLError, AssertionError, KeyError):
            if time.monotonic() >= deadline:
                raise RuntimeError('Grafana health/dashboard/data-source checks did not pass') from None
            time.sleep(2)
    print('Grafana started; Nepal dashboard and Prometheus data source provisioned.')
    # Prometheus stays inside the Compose network; query it through the collector.
    query_script = '''
import json,time
from urllib.parse import urlencode
from urllib.request import urlopen
expected={'Kathmandu, Nepal','Pokhara, Nepal','Biratnagar, Nepal'}
def query(expr):
    with urlopen('http://prometheus:9090/api/v1/query?'+urlencode({'query':expr}),timeout=5) as r:
        payload=json.load(r)
    assert payload['status']=='success'
    return payload['data']['result']
for attempt in range(30):
    try:
        up=query('up{job="weather"}')
        assert len(up)==1 and float(up[0]['value'][1])==1
        statuses=query('weather_fetch_success')
        assert {x['metric']['city'] for x in statuses}==expected
        successes=sum(float(x['value'][1]) for x in statuses)
        print('Prometheus scraped the collector and all three city status series.')
        print('Successful live provider downloads:',int(successes),'of 3.')
        if successes==3:
            temperatures=query('weather_temperature_celsius')
            assert {x['metric']['city'] for x in temperatures}==expected
            print('Live API temperature metrics present for all three cities.')
        else:
            print('Upstream API availability is separate from stack health; inspect collector logs.')
        break
    except (OSError,AssertionError,KeyError):
        if attempt==29:raise RuntimeError('Prometheus scrape checks did not pass') from None
        time.sleep(2)
'''
    subprocess.run(['docker','compose','exec','-T','weather','python','-c',query_script], check=True, timeout=90)


if __name__ == '__main__':
    check()
