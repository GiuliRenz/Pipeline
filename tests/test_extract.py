import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.extract import BASE_URL, fetch_raw_weather, save_raw_json


def _mock_response(payload: dict | None = None, status_error: Exception | None = None):
    response = MagicMock()
    response.json.return_value = payload
    if status_error:
        response.raise_for_status.side_effect = status_error
    return response


@patch("src.extract.requests.get")
def test_fetch_returns_api_payload(mock_get, raw_weather):
    mock_get.return_value = _mock_response(raw_weather)

    data = fetch_raw_weather(latitude=-38.7183, longitude=-62.2663)

    assert data == raw_weather
    args, kwargs = mock_get.call_args
    assert args[0] == BASE_URL
    assert kwargs["params"]["timezone"] == "UTC"
    assert kwargs["timeout"] == 10


@patch("src.extract.requests.get")
def test_fetch_raises_on_http_error(mock_get):
    mock_get.return_value = _mock_response(
        status_error=requests.exceptions.HTTPError("503 Service Unavailable")
    )

    with pytest.raises(requests.exceptions.HTTPError):
        fetch_raw_weather(latitude=0, longitude=0)


@patch("src.extract.requests.get")
def test_fetch_raises_on_timeout(mock_get):
    mock_get.side_effect = requests.exceptions.Timeout("timeout")

    with pytest.raises(requests.exceptions.Timeout):
        fetch_raw_weather(latitude=0, longitude=0)


def test_save_raw_json_normalizes_accents(raw_weather, tmp_path):
    path = save_raw_json(raw_weather, "Bahía Blanca", output_dir=str(tmp_path))

    assert path.name == "bahia_blanca_raw.json"
    assert json.loads(path.read_text(encoding="utf-8")) == raw_weather
