"""Open-Meteo collector with a dependency-free Prometheus endpoint."""
import json
import logging
import math
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

FIELDS = {
    'temperature_2m': ('weather_temperature_celsius', 'Air temperature in degrees Celsius.'),
    'apparent_temperature': ('weather_feels_like_celsius', 'Apparent temperature in degrees Celsius.'),
    'relative_humidity_2m': ('weather_humidity_percent', 'Relative humidity percent.'),
    'wind_speed_10m': ('weather_wind_kmh', 'Wind speed in kilometres per hour.'),
    'wind_gusts_10m': ('weather_wind_gust_kmh', 'Wind gusts in kilometres per hour.'),
    'precipitation': ('weather_precipitation_mm', 'Precipitation during the provider current interval in millimetres.'),
    'cloud_cover': ('weather_cloud_cover_percent', 'Cloud cover percent.'),
    'weather_code': ('weather_condition_code', 'WMO weather condition code.'),
}

EXPECTED_UNITS = {
    'temperature_2m': '°C', 'apparent_temperature': '°C',
    'relative_humidity_2m': '%', 'wind_speed_10m': 'km/h',
    'wind_gusts_10m': 'km/h', 'precipitation': 'mm',
    'cloud_cover': '%', 'weather_code': 'wmo code',
}


def fetch(location):
    query = urlencode({
        'latitude': location['latitude'], 'longitude': location['longitude'],
        'current': ','.join(FIELDS), 'temperature_unit': 'celsius',
        'wind_speed_unit': 'kmh', 'precipitation_unit': 'mm',
        'timeformat': 'unixtime', 'timezone': 'UTC',
    })
    request = Request('https://api.open-meteo.com/v1/forecast?' + query,
                      headers={'User-Agent': 'NepalCitiesWeather/1.0'})
    with urlopen(request, timeout=20) as response:
        payload = json.load(response)
    return parse_current(payload)


def parse_current(payload):
    current = payload['current']
    units = payload.get('current_units', {})
    for key, expected in EXPECTED_UNITS.items():
        if units.get(key) != expected:
            raise ValueError('Missing or unexpected weather unit: ' + key)
    values = {}
    for key, (metric, _) in FIELDS.items():
        value = current.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError('Missing or invalid weather field: ' + key)
        values[metric] = value
    timestamp = current['time']
    if (isinstance(timestamp, bool) or not isinstance(timestamp, (int, float))
            or not math.isfinite(timestamp) or units.get('time') != 'unixtime'):
        raise ValueError('Invalid provider timestamp')
    values['weather_source_timestamp_seconds'] = timestamp
    return values


def validate_locations(locations):
    if not isinstance(locations, list) or not locations:
        raise ValueError('Locations must be a nonempty list')
    names = set()
    for location in locations:
        if not isinstance(location, dict):
            raise ValueError('Each location must be an object')
        name = location.get('name')
        if not isinstance(name, str) or not name.strip() or name in names:
            raise ValueError('Locations must have nonempty unique names')
        names.add(name)
        for key, limit in [('latitude', 90), ('longitude', 180)]:
            value = location.get(key)
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or not -limit <= value <= limit):
                raise ValueError('Invalid location ' + key)
    return locations


class Collector:
    def __init__(self, locations, interval=300, fetcher=fetch):
        self.locations = locations
        self.interval = interval
        self.fetcher = fetcher
        self.lock = threading.Lock()
        self.samples = {}
        self.success = {loc['name']: 0 for loc in locations}

    def update_one(self, location):
        name = location['name']
        try:
            values = self.fetcher(location)
            values['weather_last_success_timestamp_seconds'] = time.time()
            with self.lock:
                self.samples[name] = values
                self.success[name] = 1
            logging.info('Updated %s', name)
        except Exception:
            with self.lock:
                self.success[name] = 0
            logging.exception('Weather fetch failed for %s; retaining last successful sample', name)

    def run(self):
        with ThreadPoolExecutor(max_workers=len(self.locations)) as pool:
            while True:
                started = time.monotonic()
                list(pool.map(self.update_one, self.locations))
                time.sleep(max(1, self.interval - (time.monotonic() - started)))

    def metrics(self):
        descriptions = dict(FIELDS.values())
        descriptions.update({
            'weather_fetch_success': 'Whether the most recent provider request succeeded.',
            'weather_source_timestamp_seconds': 'Provider weather timestamp in Unix seconds.',
            'weather_last_success_timestamp_seconds': 'Last successful download in Unix seconds.',
            'weather_poll_interval_seconds': 'Configured provider polling interval in seconds.',
        })
        lines = []
        for metric, description in descriptions.items():
            lines.extend([f'# HELP {metric} {description}', f'# TYPE {metric} gauge'])
        with self.lock:
            for location in self.locations:
                name = location['name']
                labels = 'city=' + json.dumps(name)
                values = dict(self.samples.get(name, {}))
                values['weather_fetch_success'] = self.success[name]
                values['weather_poll_interval_seconds'] = self.interval
                for metric, value in values.items():
                    lines.append(f'{metric}{{{labels}}} {value}')
        return '\n'.join(lines) + '\n'


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    interval = float(os.environ.get('WEATHER_POLL_SECONDS', '300'))
    if not math.isfinite(interval) or interval < 60:
        raise ValueError('WEATHER_POLL_SECONDS must be at least 60 (provider rate limits)')
    path = Path(os.environ.get('LOCATIONS_FILE', Path(__file__).with_name('locations.json')))
    locations = validate_locations(json.loads(path.read_text()))
    collector = Collector(locations, interval)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in ('/metrics', '/health'):
                self.send_error(404)
                return
            body = collector.metrics().encode() if self.path == '/metrics' else b'ok\n'
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; version=0.0.4; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    threading.Thread(target=collector.run, daemon=True).start()
    ThreadingHTTPServer(('0.0.0.0', 8000), Handler).serve_forever()


if __name__ == '__main__':
    main()
