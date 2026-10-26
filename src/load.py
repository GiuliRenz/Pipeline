import logging
import os

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

# Cargar variables del archivo .env
load_dotenv()

logger = logging.getLogger(__name__)


def get_db_connection():
    """
    Establece la conexión con la base de datos PostgreSQL.
    """
    try:
        connection = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            database=os.getenv("DB_NAME", "weather_db"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "postgres_password"),
            connect_timeout=5,
        )
        return connection
    except Exception as e:
        logger.error(f"Error al conectar con la base de datos: {e}")
        raise


def load_weather_data(records: list[dict]):
    """
    Inserta o actualiza los registros transformados en fact_weather_hourly.
    """
    if not records:
        logger.warning("No hay registros para cargar en la base de datos.")
        return

    query = """
        INSERT INTO fact_weather_hourly (
            location_id,
            datetime_utc,
            temperature_celsius,
            relative_humidity_pct,
            precipitation_mm,
            wind_speed_kmh,
            data_source
        )
        VALUES %s
        ON CONFLICT (location_id, datetime_utc) DO UPDATE SET
            temperature_celsius = EXCLUDED.temperature_celsius,
            relative_humidity_pct = EXCLUDED.relative_humidity_pct,
            precipitation_mm = EXCLUDED.precipitation_mm,
            wind_speed_kmh = EXCLUDED.wind_speed_kmh,
            data_source = EXCLUDED.data_source
        -- Un dato observado nunca se reemplaza por un pronóstico
        WHERE fact_weather_hourly.data_source = 'forecast'
           OR EXCLUDED.data_source = 'archive';
    """

    # Preparamos las tuplas en el orden exacto del query
    values = [
        (
            r["location_id"],
            r["datetime_utc"],
            r["temperature_celsius"],
            r["relative_humidity_pct"],
            r["precipitation_mm"],
            r["wind_speed_kmh"],
            r["data_source"],
        )
        for r in records
    ]

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # execute_values realiza inserciones masivas (bulk load) de forma muy eficiente
        execute_values(cursor, query, values)
        conn.commit()
        logger.info(f"Se cargaron exitosamente {len(records)} registros en PostgreSQL.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error al insertar datos en la BD: {e}")
        raise
    finally:
        cursor.close()
        conn.close()
