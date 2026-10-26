import json
import logging
from pathlib import Path

import requests

from src.utils import slugify

logger = logging.getLogger(__name__)

BASE_URL = "https://api.open-meteo.com/v1/forecast"


def fetch_raw_weather(latitude: float, longitude: float) -> dict:
    """
    Realiza la petición HTTP a la API de Open-Meteo para obtener
    los datos meteorológicos en bruto.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
        # Pedimos UTC explícitamente: la columna destino es datetime_utc
        "timezone": "UTC",
    }

    try:
        logger.info(f"Solicitando datos para Lat: {latitude}, Lon: {longitude}...")
        response = requests.get(BASE_URL, params=params, timeout=10)

        # Lanza una excepción si la respuesta HTTP tiene un código de error (4xx o 5xx)
        response.raise_for_status()

        data = response.json()
        logger.info("Datos obtenidos exitosamente de la API.")
        return data

    except requests.exceptions.RequestException as e:
        logger.error(f"Error al conectar con la API de Open-Meteo: {e}")
        raise


def save_raw_json(data: dict, city_name: str, output_dir: str = "data/raw") -> Path:
    """
    Guarda el diccionario JSON en un archivo local dentro de data/raw/
    para mantener un respaldo de los datos crudos.
    """
    # Crear el directorio data/raw si no existe
    dir_path = Path(output_dir)
    dir_path.mkdir(parents=True, exist_ok=True)

    # Formatear el nombre del archivo (ej. bahia_blanca_raw.json)
    file_path = dir_path / f"{slugify(city_name)}_raw.json"

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
