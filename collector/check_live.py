"""Fetch one real API response per configured city; no dashboard required."""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from collector.weather import fetch, validate_locations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('live_snapshot.json'))
    args = parser.parse_args()
    locations = validate_locations(json.loads(Path(__file__).with_name('locations.json').read_text()))
    with ThreadPoolExecutor(max_workers=len(locations)) as pool:
        values = list(pool.map(fetch, locations))
    snapshot = {
        'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
        'source': 'https://api.open-meteo.com/v1/forecast',
        'data_type': 'Model-based current-weather estimates; not station observations',
        'cities': {loc['name']: value for loc, value in zip(locations, values)},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(snapshot, indent=2) + '\n')
    print(f'Validated {len(locations)} live city responses. Saved: {args.output}')


if __name__ == '__main__':
    main()
