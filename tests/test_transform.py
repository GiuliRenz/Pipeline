import csv
import json
from datetime import datetime

import pytest

from src.transform import (
    SchemaError,
    save_clean_csv,
    save_quarantine,
    transform_weather_data,
)

LOCATION_ID = 2


# --- Camino feliz ---


def test_valid_payload_produces_one_record_per_hour(raw_weather):
    valid, rejected = transform_weather_data(raw_weather, LOCATION_ID)

    assert len(valid) == 4
    assert rejected == []
    assert valid[0] == {
        "location_id": LOCATION_ID,
        "datetime_utc": datetime(2026, 10, 7, 0, 0),
        "temperature_celsius": 14.2,
        "relative_humidity_pct": 71,
        "precipitation_mm": 0.0,
        "wind_speed_kmh": 18.5,
    }


def test_empty_lists_return_no_records(raw_weather):
    for key in raw_weather["hourly"]:
        raw_weather["hourly"][key] = []

    assert transform_weather_data(raw_weather, LOCATION_ID) == ([], [])


# --- Validación por registro: las filas inválidas van a cuarentena sin frenar el lote ---


@pytest.mark.parametrize(
    ("api_field", "bad_value"),
    [
        ("relative_humidity_2m", 150),
        ("relative_humidity_2m", -5),
        ("temperature_2m", -120.0),
        ("temperature_2m", 75.0),
        ("precipitation", -1.0),
        ("wind_speed_10m", -3.0),
        ("temperature_2m", "N/A"),
    ],
)
def test_out_of_range_value_is_rejected(raw_weather, api_field, bad_value):
    raw_weather["hourly"][api_field][1] = bad_value

    valid, rejected = transform_weather_data(raw_weather, LOCATION_ID)

    assert len(valid) == 3
    assert len(rejected) == 1
    assert rejected[0]["datetime_utc"] == "2026-10-07T01:00"
    assert rejected[0]["errors"]


def test_invalid_date_format_is_rejected(raw_weather):
    raw_weather["hourly"]["time"][0] = "07/10/2026 00:00"

    valid, rejected = transform_weather_data(raw_weather, LOCATION_ID)

    assert len(valid) == 3
    assert any("datetime_utc" in err for err in rejected[0]["errors"])


def test_single_null_measure_is_kept(raw_weather):
    raw_weather["hourly"]["temperature_2m"][2] = None

    valid, rejected = transform_weather_data(raw_weather, LOCATION_ID)

    assert len(valid) == 4
    assert rejected == []
    assert valid[2]["temperature_celsius"] is None


def test_record_with_all_measures_null_is_rejected(raw_weather):
    for field in ("temperature_2m", "relative_humidity_2m", "precipitation", "wind_speed_10m"):
        raw_weather["hourly"][field][3] = None

    valid, rejected = transform_weather_data(raw_weather, LOCATION_ID)

    assert len(valid) == 3
    assert "ninguna medición" in rejected[0]["errors"][0]


# --- Validación estructural: errores que invalidan todo el lote ---


def test_missing_hourly_block_raises(raw_weather):
    del raw_weather["hourly"]

    with pytest.raises(SchemaError, match="hourly"):
        transform_weather_data(raw_weather, LOCATION_ID)


def test_renamed_api_field_raises(raw_weather):
    # Simula que la API renombra un campo sin aviso
    raw_weather["hourly"]["temp_2m"] = raw_weather["hourly"].pop("temperature_2m")

    with pytest.raises(SchemaError, match="temperature_2m"):
        transform_weather_data(raw_weather, LOCATION_ID)


def test_mismatched_list_lengths_raise(raw_weather):
    raw_weather["hourly"]["precipitation"].pop()

    with pytest.raises(SchemaError, match="distinto largo"):
        transform_weather_data(raw_weather, LOCATION_ID)


def test_non_utc_payload_raises(raw_weather):
    raw_weather["utc_offset_seconds"] = -10800

    with pytest.raises(SchemaError, match="UTC"):
        transform_weather_data(raw_weather, LOCATION_ID)


# --- Persistencia local ---


def test_save_clean_csv_writes_all_rows(raw_weather, tmp_path):
    valid, _ = transform_weather_data(raw_weather, LOCATION_ID)

    path = save_clean_csv(valid, "Bahía Blanca", output_dir=str(tmp_path))

    assert path.name == "bahia_blanca_clean.csv"
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 4
    assert rows[0]["datetime_utc"] == "2026-10-07 00:00:00"


def test_save_clean_csv_skips_empty_records(tmp_path):
    assert save_clean_csv([], "Cordoba", output_dir=str(tmp_path)) is None
    assert list(tmp_path.iterdir()) == []


def test_save_quarantine_appends_json_lines(raw_weather, tmp_path):
    raw_weather["hourly"]["relative_humidity_2m"][0] = 150
    _, rejected = transform_weather_data(raw_weather, LOCATION_ID)

    save_quarantine(rejected, "Cordoba", output_dir=str(tmp_path))
    path = save_quarantine(rejected, "Cordoba", output_dir=str(tmp_path))

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    entry = json.loads(lines[0])
    assert entry["relative_humidity_pct"] == 150
    assert "quarantined_at" in entry
