import csv
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from src.schemas import WeatherRecord
from src.utils import slugify

logger = logging.getLogger(__name__)

# Variables horarias que pedimos a la API y la columna destino de cada una
HOURLY_FIELDS = {
    "temperature_2m": "temperature_celsius",
    "relative_humidity_2m": "relative_humidity_pct",
    "precipitation": "precipitation_mm",
    "wind_speed_10m": "wind_speed_kmh",
}


class SchemaError(ValueError):
    """
    La respuesta de la API tiene una estructura inesperada (campos faltantes,
    listas de distinto largo, zona horaria incorrecta). Afecta a todo el lote,
    por lo que no es seguro procesar ninguna fila.
    """


def _validate_structure(raw_data: dict) -> dict:
    """
    Verifica la estructura general de la respuesta y devuelve el bloque 'hourly'.
    """
    offset = raw_data.get("utc_offset_seconds", 0)
    if offset != 0:
        raise SchemaError(f"Se esperaban horas en UTC, pero utc_offset_seconds={offset}")

    hourly = raw_data.get("hourly")
    if not isinstance(hourly, dict):
        raise SchemaError("La respuesta no contiene el bloque 'hourly'")

    expected = ["time", *HOURLY_FIELDS]
    missing = [field for field in expected if field not in hourly]
    if missing:
        raise SchemaError(f"Faltan campos en 'hourly': {missing}")

    # zip() truncaría en silencio si las listas paralelas tienen distinto largo
    lengths = {field: len(hourly[field]) for field in expected}
    if len(set(lengths.values())) > 1:
        raise SchemaError(f"Las listas de 'hourly' tienen distinto largo: {lengths}")

    return hourly


def transform_weather_data(
    raw_data: dict, location_id: int, data_source: str = "forecast"
) -> tuple[list[dict], list[dict]]:
    """
    Toma el diccionario JSON en crudo de Open-Meteo, desanida las listas paralelas
    de 'hourly' y valida cada registro contra WeatherRecord.

    data_source indica el origen del lote: 'forecast' (pronóstico)
    o 'archive' (histórico observado).

    Devuelve (registros_validos, registros_rechazados). Los rechazados incluyen
    el detalle de los errores para poder guardarlos en cuarentena.
    """
    hourly = _validate_structure(raw_data)

    valid_records = []
    rejected_records = []

    for i, timestamp in enumerate(hourly["time"]):
        candidate = {
            "location_id": location_id,
            "datetime_utc": timestamp,
            "data_source": data_source,
        }
        for api_field, column in HOURLY_FIELDS.items():
            candidate[column] = hourly[api_field][i]

        try:
            record = WeatherRecord(**candidate)
        except ValidationError as e:
            errors = [f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()]
            rejected_records.append({**candidate, "errors": errors})
            continue

        valid_records.append(record.model_dump())

    logger.info(
        f"Transformación completada: {len(valid_records)} válidos, "
        f"{len(rejected_records)} rechazados."
    )
    if rejected_records:
        logger.warning(f"Ejemplo de registro rechazado: {rejected_records[0]}")

    return valid_records, rejected_records


def save_clean_csv(
    records: list[dict], city_name: str, output_dir: str = "data/processed"
) -> Path | None:
    """
    Guarda los registros transformados en un archivo CSV limpio en data/processed/
    """
    if not records:
        logger.warning("No hay registros para guardar en CSV.")
        return None

    dir_path = Path(output_dir)
    dir_path.mkdir(parents=True, exist_ok=True)

    file_path = dir_path / f"{slugify(city_name)}_clean.csv"

    fieldnames = list(records[0].keys())

    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    logger.info(f"Archivo CSV limpio guardado en: {file_path}")
    return file_path


def save_quarantine(
    records: list[dict], city_name: str, output_dir: str = "data/quarantine"
) -> Path | None:
    """
    Agrega los registros rechazados a un archivo JSON Lines en data/quarantine/
    para poder auditarlos o reprocesarlos sin bloquear la carga de los válidos.
    """
    if not records:
        return None

    dir_path = Path(output_dir)
    dir_path.mkdir(parents=True, exist_ok=True)

    file_path = dir_path / f"{slugify(city_name)}_rejected.jsonl"
    quarantined_at = datetime.now(UTC).isoformat()

    with open(file_path, "a", encoding="utf-8") as f:
        for record in records:
            line = {**record, "quarantined_at": quarantined_at}
            f.write(json.dumps(line, ensure_ascii=False, default=str) + "\n")

    logger.warning(f"{len(records)} registros enviados a cuarentena: {file_path}")
    return file_path
