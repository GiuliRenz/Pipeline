from datetime import date, timedelta
from unittest.mock import patch

import pytest
import requests

import main

LOCATIONS = [
    {"location_id": 1, "city_name": "Buenos Aires", "latitude": -34.6, "longitude": -58.4},
    {"location_id": 2, "city_name": "Bahía Blanca", "latitude": -38.7, "longitude": -62.3},
]


@pytest.fixture
def pipeline_mocks(raw_weather, tmp_path, monkeypatch):
    """Reemplaza la API y la BD para ejecutar el pipeline completo sin dependencias externas."""
    monkeypatch.chdir(tmp_path)  # los archivos de data/ se escriben en un directorio temporal
    with (
        patch("main.get_locations", return_value=LOCATIONS),
        patch("main.fetch_raw_weather", return_value=raw_weather) as fetch,
        patch("main.load_weather_data") as load,
    ):
        yield fetch, load


def test_pipeline_succeeds_when_all_cities_load(pipeline_mocks):
    _, load = pipeline_mocks

    assert main.run_pipeline() is True
    assert load.call_count == 2


def test_pipeline_continues_and_reports_failure(pipeline_mocks, raw_weather):
    fetch, load = pipeline_mocks
    fetch.side_effect = [requests.exceptions.Timeout("timeout"), raw_weather]

    assert main.run_pipeline() is False
    # La segunda ciudad se procesa igual aunque la primera haya fallado
    assert load.call_count == 1


def test_backfill_uses_archive_api(pipeline_mocks, raw_weather):
    _, load = pipeline_mocks
    period = (date(2024, 1, 1), date(2024, 12, 31))

    with patch("main.fetch_historical_weather", return_value=raw_weather) as fetch_hist:
        assert main.run_pipeline(export_csv=False, backfill=period) is True

    fetch_hist.assert_any_call(-34.6, -58.4, *period)
    loaded = load.call_args.kwargs["records"]
    assert {r["data_source"] for r in loaded} == {"archive"}


def test_parse_args_backfill_defaults():
    args = main.parse_args(["--backfill"])

    assert args.end_date == date.today() - timedelta(days=main.ARCHIVE_DELAY_DAYS)
    assert (args.end_date - args.start_date).days == main.DEFAULT_BACKFILL_DAYS


@pytest.mark.parametrize(
    "argv",
    [
        ["--backfill", "--start-date", "2025-02-01", "--end-date", "2025-01-01"],
        ["--start-date", "2025-01-01"],
    ],
)
def test_parse_args_rejects_invalid_combinations(argv):
    with pytest.raises(SystemExit):
        main.parse_args(argv)
