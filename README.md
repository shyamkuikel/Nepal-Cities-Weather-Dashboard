# Nepal Cities Weather Dashboard

**Nepal adaptation maintained by Shyam Prasad Kuikel**

A Python, Prometheus and Grafana project comparing weather estimates in **Kathmandu, Pokhara and Biratnagar**. It downloads real Open-Meteo API responses and displays temperature, feels-like temperature, humidity, wind, gusts, precipitation, cloud cover and weather conditions.

**These are model-based estimates, not measurements from Nepal's ground stations.** The application does not invent values or simulated histories. Charts accumulate data only while the services run. This project does not collect PM2.5 or train a machine-learning model.

## Cities and units

| City | Latitude | Longitude |
| --- | ---: | ---: |
| Kathmandu | 27.70169 | 85.32060 |
| Pokhara | 28.26689 | 83.96851 |
| Biratnagar | 26.45505 | 87.27007 |

Coordinates are representative place points from the Open-Meteo Geocoding API, not weather-station locations or city-wide averages. [Saved location records](docs/location_sources.json).

The dashboard uses **Nepal time (UTC+05:45)**, **degrees Celsius**, **km/h** and **millimetres**. UTC Unix timestamps are retained internally.

## Features

- City-specific cards and comparison charts with a city filter.
- Provider downloads every five minutes; dashboard refresh every ten seconds.
- Download status, source-data age and time since the last successful download.
- Up to 30 days of collected history in persistent Prometheus storage.
- Automatic dashboard provisioning, outage handling and automated tests.

The collector downloads and validates data, Prometheus stores metrics, and Grafana displays them. Dashboard refresh does not create new source estimates; provider updates happen independently.

## Verify the data source

The [saved API snapshot](docs/api_snapshot.json) contains actual responses retrieved on **27 October 2026**, with retrieval and provider timestamps. It is a dated verification sample, not a live display. See [verification](VERIFICATION.md) for checks performed and runtime limits.


Example API responses retrieved 27 October 2026, 17:48:04 Nepal time (dated sample):

| City | Temperature (°C) | Humidity (%) | Wind (km/h) |
| --- | ---: | ---: | ---: |
| Kathmandu, Nepal | 20.2 | 68 | 2.9 |
| Pokhara, Nepal | 20.3 | 46 | 0.2 |
| Biratnagar, Nepal | 26.7 | 71 | 1.4 |

These values are preserved in the linked JSON; they are not presented as current conditions.

With Python 3.10 or newer, fetch a fresh sample from the repository root:

```sh
python3 -m collector.check_live --output live_snapshot.json
```

This makes one request per city, validates fields and units, and saves returned values. It needs internet access but no Docker or pip packages. The dashboard never uses the saved sample as a fallback.

## Run locally

Install Docker Desktop with Compose on macOS/Windows, or Docker Engine and the Compose plugin on Linux. Start Docker, then:

```sh
git clone https://github.com/shyamkuikel/Nepal-Cities-Weather-Dashboard.git
cd Nepal-Cities-Weather-Dashboard
cp .env.example .env
chmod 600 .env
```

Edit `.env` and choose your own `GRAFANA_ADMIN_USER` and `GRAFANA_ADMIN_PASSWORD`. Both are intentionally blank in the template; private `.env` files are excluded from Git.

```sh
sh start.sh
```

After startup completes, open [Nepal Cities Weather](http://localhost:3000/d/nepal-cities-weather) and sign in with your chosen credentials. Initial charts have no history; allow time for the first download and scrape.

Windows PowerShell users can run these commands after cloning and entering the repository:

```powershell
Copy-Item .env.example .env
notepad .env
# Fill both credential fields, save and close the editor.
docker compose config --quiet
docker compose up -d --build
```

Only Grafana is published to the host, bound to `127.0.0.1`. **The GitHub link shares source code; it does not host a running Grafana dashboard.**

## Configuration

| Setting | Default | Location |
| --- | --- | --- |
| Provider download interval | 300 seconds; minimum 60 | `WEATHER_POLL_SECONDS` in `.env` |
| Grafana port | 3000 | `GRAFANA_PORT` in `.env` |
| Dashboard refresh | 10 seconds | Grafana refresh menu / dashboard JSON |
| Chart time zone | Asia/Kathmandu | Dashboard JSON |
| Metrics scrape | 10 seconds | `prometheus/prometheus.yml` |
| History retention | 30 days | `compose.yaml` |
| City coordinates | Three Nepal cities | `collector/locations.json` |

Changing city names also requires updating card titles and queries in `grafana/dashboards/weather.json`. Comparison charts discover labels automatically. Restart `weather` after changing coordinates. Apply environment or Compose changes with `docker compose up -d --build`.

## Interpretation

Precipitation is the provider's **current-interval amount, not a daily total**. Do not sum repeated scrapes to estimate rainfall. Estimates represent a model grid point near the requested coordinates; terrain and microclimates can differ from conditions at a particular street or station.

Failed downloads retain the last successful sample and mark the city as failed. Check download status and source age. Data are not backfilled while the computer sleeps or services stop. The collector cache resets on restart; Prometheus history persists in its named volume. `/health` checks HTTP availability, not upstream data quality.

## Checks and operation

No pip dependencies are needed for the collector or tests:

```sh
python3 -m unittest discover -s tests -v
sh -n start.sh
# With Docker installed and private credentials configured:
docker compose config --quiet
```

Tests use fixtures. The separate live-check command verifies API connectivity. GitHub Actions runs unit tests and shell checks, then starts the actual Docker stack with disposable credentials. It verifies Grafana dashboard provisioning and Prometheus scraping. Live provider availability is reported separately from stack health.

```sh
docker compose ps
docker compose logs --tail=50 weather prometheus grafana
docker compose down
```

Normal `docker compose down` preserves named volumes. Keep Docker running and the computer awake for continuous collection. `.env` credentials initialize a new Grafana database; existing passwords must be changed within Grafana.

## Files to review

| File | Purpose |
| --- | --- |
| [collector/weather.py](collector/weather.py) | API requests, validation and metrics |
| [collector/check_live.py](collector/check_live.py) | Repeatable live-data check |
| [collector/locations.json](collector/locations.json) | City coordinates |
| [grafana/dashboards/weather.json](grafana/dashboards/weather.json) | Dashboard definition |
| [compose.yaml](compose.yaml) | Local services |
| [tests/test_weather.py](tests/test_weather.py) | Automated tests |
| [tests/check_stack.py](tests/check_stack.py) | Running Docker-stack integration checks |
| [VERIFICATION.md](VERIFICATION.md) | Verified behavior and remaining checks |

## Sources and attribution

[Weather data by Open-Meteo](https://open-meteo.com/): [API documentation](https://open-meteo.com/en/docs), [terms](https://open-meteo.com/en/terms) and [usage limits](https://open-meteo.com/en/pricing). Review terms before commercial use or increasing polling.

The Nepal adaptation builds on the supplied MIT-licensed `Grafana_Page` project. The original copyright notice is retained. See [NOTICE.md](NOTICE.md) and [LICENSE](LICENSE) for attribution.
