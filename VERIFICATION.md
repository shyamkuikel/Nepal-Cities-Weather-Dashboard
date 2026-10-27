# Verification

Checks performed on 27 October 2026 for the Nepal adaptation:

- Nine unit tests passed: response parsing, invalid-value and wrong-unit rejection, stale-data preservation, independent city failures, dashboard panel IDs and refresh, Nepal city/query/unit consistency, and invalid/duplicate location rejection.
- Live Open-Meteo responses were fetched and parsed for all three cities. Numeric fields, timestamps and declared Celsius, km/h and mm units passed validation. A dated sample is saved in [docs/api_snapshot.json](docs/api_snapshot.json).
- The collector was started as a real Python process. `/health` returned `ok`, and `/metrics` exposed temperature and successful-fetch metrics for all three cities using live provider data. An example is preserved in [docs/metrics_sample.txt](docs/metrics_sample.txt).
- The repeatable `python -m collector.check_live` command also succeeded for all three cities.
- [GitHub Actions run 1](https://github.com/shyamkuikel/Nepal-Cities-Weather-Dashboard/actions/runs/40501327617) passed all nine tests, startup-script syntax checks and Docker Compose configuration validation.
- `sh -n start.sh` passed. Configuration JSON and YAML syntax and relative documentation links were checked.

## Docker integration check

[GitHub Actions run 3](https://github.com/shyamkuikel/Nepal-Cities-Weather-Dashboard/actions/runs/40502023738) started the real Docker services and passed:

- Grafana health and database availability.
- Automatic provisioning of the Nepal dashboard (41 panels, Asia/Kathmandu time zone).
- Provisioning of the Prometheus data source.
- Successful Prometheus scraping and city status series for all three locations.
- Successful live API downloads and temperature metrics for all three cities in that run.

The integration script reports provider availability separately from stack health because upstream outages can occur. This run had three successful provider downloads. The continuous integration actions were updated to Node.js 24 versions after an older-action deprecation warning, and the runner is pinned to Ubuntu 24.04.

**Remaining scope:** browser rendering and visual layout inside Grafana have not been manually inspected. Docker is unavailable in the local preparation environment; service startup and provisioning were verified on GitHub's Linux runner. This is not a validation against station observations or a test of forecast accuracy.

## Recheck

```sh
python3 -m unittest discover -s tests -v
sh -n start.sh
python3 -m collector.check_live --output live_snapshot.json
# With Docker installed and private .env credentials configured:
docker compose config --quiet
sh start.sh
```

The saved sample is evidence of API connectivity, not independent validation against ground-station measurements, a historical dataset, or a performance study of forecast accuracy. Provider estimates and retrieval times are separate. An API outage produces a failure indicator; invented values are never substituted.
