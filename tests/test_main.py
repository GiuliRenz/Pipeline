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
