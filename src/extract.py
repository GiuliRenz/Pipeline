import json
import logging
from datetime import date
from pathlib import Path

import requests

from src.utils import slugify

logger = logging.getLogger(__name__)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
HOURLY_VARIABLES = "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
# Días pasados que incluye el pronóstico: cubren el retraso con que la Archive API publica datos
FORECAST_PAST_DAYS = 7


def _get_json(url: str, params: dict, timeout: int) -> dict:
    """
    Realiza la petición HTTP y devuelve el JSON. Lanza una excepción ante errores de red o HTTP.
    """
    try:
        response = requests.get(url, params=params, timeout=timeout)

        # Lanza una excepción si la respuesta HTTP tiene un código de error (4xx o 5xx)
        response.raise_for_status()

        data = response.json()
        logger.info("Datos obtenidos exitosamente de la API.")
        return data

    except requests.exceptions.RequestException as e:
        logger.error(f"Error al conectar con la API de Open-Meteo: {e}")
        raise


def fetch_raw_weather(latitude: float, longitude: float) -> dict:
    """
    Obtiene el pronóstico horario (últimos y próximos 7 días) desde la Forecast API de Open-Meteo.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": HOURLY_VARIABLES,
        "past_days": FORECAST_PAST_DAYS,
        # Pedimos UTC explícitamente: la columna destino es datetime_utc
        "timezone": "UTC",
    }
    logger.info(f"Solicitando pronóstico para Lat: {latitude}, Lon: {longitude}...")
    return _get_json(FORECAST_URL, params, timeout=10)


def fetch_historical_weather(
    latitude: float, longitude: float, start_date: date, end_date: date
) -> dict:
    """
    Obtiene datos horarios observados (reanálisis ERA5) desde la Archive API de Open-Meteo.
    La respuesta tiene la misma estructura que la Forecast API, por lo que reutiliza transform.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "hourly": HOURLY_VARIABLES,
        "timezone": "UTC",
    }
    logger.info(
        f"Solicitando histórico {start_date} → {end_date} para Lat: {latitude}, Lon: {longitude}..."
    )
    # Rangos de varios años generan respuestas grandes: damos más margen de tiempo
    return _get_json(ARCHIVE_URL, params, timeout=60)


def save_raw_json(
    data: dict, city_name: str, output_dir: str = "data/raw", data_source: str = "forecast"
) -> Path:
    """
    Guarda el diccionario JSON en un archivo local dentro de data/raw/
    para mantener un respaldo de los datos crudos.
    """
    # Crear el directorio data/raw si no existe
    dir_path = Path(output_dir)
    dir_path.mkdir(parents=True, exist_ok=True)

    # Formatear el nombre del archivo (ej. bahia_blanca_forecast_raw.json)
    file_path = dir_path / f"{slugify(city_name)}_{data_source}_raw.json"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    logger.info(f"Archivo JSON crudo guardado en: {file_path}")
    return file_path


# Bloque de prueba individual del módulo: python -m src.extract
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    # Prueba rápida llamando a la API para Bahía Blanca
    city = "Bahía Blanca"
    lat, lon = -38.7183, -62.2663

    raw_data = fetch_raw_weather(latitude=lat, longitude=lon)
    save_raw_json(data=raw_data, city_name=city)
