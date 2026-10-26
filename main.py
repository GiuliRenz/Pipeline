import logging
import sys

from src.extract import fetch_raw_weather, save_raw_json
from src.load import get_db_connection, load_weather_data
from src.transform import save_clean_csv, save_quarantine, transform_weather_data

logger = logging.getLogger(__name__)


def get_locations() -> list[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT location_id, city_name, latitude, longitude FROM dim_locations;")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return [
        {
            "location_id": row[0],
            "city_name": row[1],
            "latitude": float(row[2]),
            "longitude": float(row[3]),
        }
        for row in rows
    ]


def run_pipeline(export_csv: bool = True) -> bool:
    """
    Ejecuta el flujo ETL completo. Si export_csv es True, guarda además un CSV en data/processed/
    Devuelve True solo si todas las ciudades se procesaron sin errores.
    """
    logger.info("=== INICIANDO PIPELINE ETL BATCH ===")
    locations = get_locations()
    failed_cities = []

    for loc in locations:
        city_id = loc["location_id"]
        city_name = loc["city_name"]
        lat = loc["latitude"]
        lon = loc["longitude"]

        logger.info(f"--- Procesando: {city_name} (ID: {city_id}) ---")

        try:
            # 1. EXTRACT
            raw_data = fetch_raw_weather(latitude=lat, longitude=lon)
            save_raw_json(data=raw_data, city_name=city_name)

            # 2. TRANSFORM + VALIDACIÓN
            clean_records, rejected_records = transform_weather_data(
                raw_data=raw_data, location_id=city_id
            )
            save_quarantine(records=rejected_records, city_name=city_name)

            # Exportación opcional a CSV
            if export_csv:
                save_clean_csv(records=clean_records, city_name=city_name)

            # 3. LOAD
            load_weather_data(records=clean_records)

        except Exception as e:
            logger.error(f"Falló el procesamiento para {city_name}: {e}")
            failed_cities.append(city_name)
            continue

    if failed_cities:
        logger.error(
            f"=== PIPELINE FINALIZADO CON ERRORES: {len(failed_cities)}/{len(locations)} "
            f"ciudades fallaron ({', '.join(failed_cities)}) ==="
        )
        return False

    logger.info(f"=== PIPELINE COMPLETADO EXITOSAMENTE: {len(locations)} ciudades ===")
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    # Código de salida != 0 para que un orquestador (cron, Airflow, CI) detecte el fallo
    sys.exit(0 if run_pipeline(export_csv=True) else 1)
