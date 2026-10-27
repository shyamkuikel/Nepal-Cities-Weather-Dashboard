# Verification

Checks performed on 27 October 2026 for the Nepal adaptation:

- Nine unit tests passed: response parsing, invalid-value and wrong-unit rejection, stale-data preservation, independent city failures, dashboard panel IDs and refresh, Nepal city/query/unit consistency, and invalid/duplicate location rejection.
- Live Open-Meteo responses were fetched and parsed for all three cities. Numeric fields, timestamps and declared Celsius, km/h and mm units passed validation. A dated sample is saved in [docs/api_snapshot.json](docs/api_snapshot.json).
- The collector was started as a real Python process. `/health` returned `ok`, and `/metrics` exposed temperature and successful-fetch metrics for all three cities using live provider data. An example is preserved in [docs/metrics_sample.txt](docs/metrics_sample.txt).
- The repeatable `python -m collector.check_live` command also succeeded for all three cities.
- [GitHub Actions run 1](https://github.com/shyamkuikel/Nepal-Cities-Weather-Dashboard/actions/runs/40501327617) passed all nine tests, startup-script syntax checks and Docker Compose configuration validation.
- `sh -n start.sh` passed. Configuration JSON and YAML syntax and relative documentation links were checked.

**Runtime limit:** Docker is unavailable in the preparation environment. The complete Docker/Grafana/Prometheus stack and rendered Grafana panels have not been run here. The supplied GitHub Actions workflow validates Compose configuration; an end-to-end local launch remains the next runtime check. No dashboard screenshot or successful container launch is claimed.

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
