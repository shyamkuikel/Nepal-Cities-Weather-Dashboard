import json
import unittest
from collector.weather import Collector, FIELDS, EXPECTED_UNITS, parse_current, validate_locations


def payload():
    return {
        'current': {**{key: 12.5 for key in FIELDS}, 'time': 1790000000},
        'current_units': {**EXPECTED_UNITS, 'time': 'unixtime'},
    }


class WeatherTests(unittest.TestCase):
    def test_all_fields_and_source_time(self):
        parsed = parse_current(payload())
        self.assertEqual(len(parsed), len(FIELDS) + 1)
        self.assertEqual(parsed['weather_temperature_celsius'], 12.5)
        self.assertEqual(parsed['weather_source_timestamp_seconds'], 1790000000)

    def test_invalid_data_is_not_published_as_zero(self):
        for invalid in (None, float('nan'), 'bad', True):
            data = payload()
            data['current']['temperature_2m'] = invalid
            with self.assertRaises(ValueError):
                parse_current(data)

    def test_outage_preserves_sample_but_reports_failure(self):
        location = {'name': 'Kathmandu, Nepal'}
        collector = Collector([location], fetcher=lambda _: parse_current(payload()))
        collector.update_one(location)
        before = dict(collector.samples[location['name']])
        collector.fetcher = lambda _: (_ for _ in ()).throw(TimeoutError('test outage'))
        with self.assertLogs(level='ERROR'):
            collector.update_one(location)
        self.assertEqual(collector.samples[location['name']], before)
        self.assertEqual(collector.success[location['name']], 0)
        self.assertIn('weather_fetch_success{city="Kathmandu, Nepal"} 0', collector.metrics())

    def test_independent_city_failure(self):
        locations = [{'name': 'good'}, {'name': 'bad'}]
        def fetcher(loc):
            if loc['name'] == 'bad':
                raise ValueError('failed')
            return parse_current(payload())
        collector = Collector(locations, fetcher=fetcher)
        collector.update_one(locations[0])
        with self.assertLogs(level='ERROR'):
            collector.update_one(locations[1])
        self.assertEqual(collector.success, {'good': 1, 'bad': 0})
        self.assertNotIn('weather_temperature_celsius{city="bad"}', collector.metrics())

    def test_dashboard_refresh_and_unique_panel_ids(self):
        with open('grafana/dashboards/weather.json') as source:
            dashboard = json.load(source)
        self.assertEqual(dashboard['refresh'], '10s')
        ids = [panel['id'] for panel in dashboard['panels']]
        self.assertEqual(len(ids), len(set(ids)))

    def test_wrong_units_are_rejected(self):
        data = payload()
        data['current_units']['temperature_2m'] = '°F'
        with self.assertRaises(ValueError):
            parse_current(data)

    def test_nepal_cities_and_dashboard_match(self):
        with open('collector/locations.json') as source:
            locations = validate_locations(json.load(source))
        self.assertEqual({x['name'] for x in locations},
                         {'Kathmandu, Nepal', 'Pokhara, Nepal', 'Biratnagar, Nepal'})
        with open('grafana/dashboards/weather.json') as source:
            dashboard = json.load(source)
        self.assertEqual(dashboard['timezone'], 'Asia/Kathmandu')
        for location in locations:
            city = location['name']
            self.assertTrue(any(f'city="{city}"' in target.get('expr', '')
                                for panel in dashboard['panels']
                                for target in panel.get('targets', [])))
        for panel in dashboard['panels']:
            for target in panel.get('targets', []):
                expr = target.get('expr', '')
                unit = panel.get('fieldConfig', {}).get('defaults', {}).get('unit')
                if 'weather_temperature_celsius' in expr or 'weather_feels_like_celsius' in expr:
                    self.assertEqual(unit, 'celsius')
                if 'weather_wind_' in expr:
                    self.assertEqual(unit, 'velocitykmh')
                if 'weather_precipitation_mm' in expr:
                    self.assertEqual(unit, 'lengthmm')

    def test_invalid_coordinates_are_rejected(self):
        for latitude in (91, -91, float('nan'), True, None):
            with self.assertRaises(ValueError):
                validate_locations([{'name': 'test', 'latitude': latitude, 'longitude': 85}])

    def test_duplicate_city_names_are_rejected(self):
        location = {'name': 'Pokhara, Nepal', 'latitude': 28.26689, 'longitude': 83.96851}
        with self.assertRaises(ValueError):
            validate_locations([location, location])


if __name__ == '__main__':
    unittest.main()
