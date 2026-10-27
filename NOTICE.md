# Attribution

The Nepal configuration and adaptation are maintained by **Shyam Prasad Kuikel**.

This project adapts the supplied `Grafana_Page` dashboard and collector. Its original MIT notice, `Copyright (c) 2026 regmi-sijan`, is retained in [LICENSE](LICENSE). The Nepal adaptation changes locations, metric names, units, dashboard time zone and labels, adds unit and coordinate validation, and updates tests and documentation. It is not a new weather prediction model.

Weather estimates: [Open-Meteo](https://open-meteo.com/), with data attribution under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). API service terms are separate from the data license.

Location coordinates: Open-Meteo's [Geocoding API](https://open-meteo.com/en/docs/geocoding-api), based on GeoNames. Retrieved records are in [docs/location_sources.json](docs/location_sources.json).

Grafana, Prometheus, Python and Docker retain their respective licenses.
