from datetime import datetime

import pytest

from src.load import get_db_connection, load_weather_data

pytestmark = pytest.mark.integration

# Fecha fuera del rango que carga el pipeline, para no pisar datos reales
TEST_DATETIME = datetime(1990, 1, 1, 0, 0)


@pytest.fixture
def db_conn():
    try:
        conn = get_db_connection()
    except Exception:
        pytest.skip("PostgreSQL no disponible")
    yield conn
    conn.close()


@pytest.fixture
def location_id(db_conn):
    with db_conn.cursor() as cur:
        cur.execute("SELECT location_id FROM dim_locations ORDER BY location_id LIMIT 1;")
        row = cur.fetchone()
    if row is None:
        pytest.skip("dim_locations está vacía; ejecutá sql/init_db.sql")
    yield row[0]
    with db_conn.cursor() as cur:
        cur.execute(
            "DELETE FROM fact_weather_hourly WHERE location_id = %s AND datetime_utc = %s;",
            (row[0], TEST_DATETIME),
        )
    db_conn.commit()


def _record(location_id: int, temperature: float) -> dict:
    return {
        "location_id": location_id,
        "datetime_utc": TEST_DATETIME,
        "temperature_celsius": temperature,
        "relative_humidity_pct": 60,
        "precipitation_mm": 0.0,
        "wind_speed_kmh": 10.0,
    }


def _fetch_rows(db_conn, location_id: int) -> list[tuple]:
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT temperature_celsius FROM fact_weather_hourly "
            "WHERE location_id = %s AND datetime_utc = %s;",
            (location_id, TEST_DATETIME),
        )
        return cur.fetchall()


def test_load_is_idempotent_and_upserts(db_conn, location_id):
    load_weather_data([_record(location_id, 10.0)])
    load_weather_data([_record(location_id, 12.5)])

    rows = _fetch_rows(db_conn, location_id)

    # Re-ejecutar el ETL no duplica filas: actualiza la existente
    assert len(rows) == 1
    assert float(rows[0][0]) == 12.5
