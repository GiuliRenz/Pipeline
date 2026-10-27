import argparse
import logging
import sys
from datetime import date, timedelta

from src.extract import (
    FORECAST_PAST_DAYS,
    fetch_historical_weather,
    fetch_raw_weather,
    save_raw_json,
)
from src.load import get_db_connection, load_weather_data
from src.transform import save_clean_csv, save_quarantine, transform_weather_data

logger = logging.getLogger(__name__)

# La Archive API publica los datos observados con unos días de retraso;
# el pronóstico diario (past_days) cubre ese hueco hasta que llega el dato observado
ARCHIVE_DELAY_DAYS = FORECAST_PAST_DAYS
DEFAULT_BACKFILL_DAYS = 730


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


def process_city(
    loc: dict, export_csv: bool = True, backfill: tuple[date, date] | None = None
) -> int:
    """
    Ejecuta extract → transform → load para una ciudad y devuelve los registros cargados.
    Lanza una excepción si algo falla; la usan tanto run_pipeline como el DAG de Airflow,
    donde cada ciudad es una tarea independiente con sus propios reintentos.
    """
    data_source = "archive" if backfill else "forecast"
    city_name = loc["city_name"]
    logger.info(f"--- Procesando: {city_name} (ID: {loc['location_id']}) ---")

    # 1. EXTRACT
    if backfill:
        raw_data = fetch_historical_weather(loc["latitude"], loc["longitude"], *backfill)
    else:
        raw_data = fetch_raw_weather(latitude=loc["latitude"], longitude=loc["longitude"])
    save_raw_json(data=raw_data, city_name=city_name, data_source=data_source)

    # 2. TRANSFORM + VALIDACIÓN
    clean_records, rejected_records = transform_weather_data(
        raw_data=raw_data, location_id=loc["location_id"], data_source=data_source
    )
    save_quarantine(records=rejected_records, city_name=city_name)

    # Exportación opcional a CSV
    if export_csv:
        save_clean_csv(records=clean_records, city_name=city_name)

    # 3. LOAD
    load_weather_data(records=clean_records)
    return len(clean_records)


def run_pipeline(export_csv: bool = True, backfill: tuple[date, date] | None = None) -> bool:
    """
    Ejecuta el flujo ETL completo. Si export_csv es True, guarda además un CSV en data/processed/
    Si se indica backfill=(inicio, fin), carga datos observados de la Archive API en ese rango
    en lugar del pronóstico.
    Devuelve True solo si todas las ciudades se procesaron sin errores.
    """
    data_source = "archive" if backfill else "forecast"
    logger.info(f"=== INICIANDO PIPELINE ETL BATCH ({data_source}) ===")
    locations = get_locations()
    failed_cities = []

    for loc in locations:
        city_name = loc["city_name"]
        try:
            process_city(loc, export_csv=export_csv, backfill=backfill)
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pipeline ETL de datos meteorológicos.")
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Carga datos históricos observados (Archive API) en lugar del pronóstico.",
    )
    parser.add_argument(
        "--start-date",
        type=date.fromisoformat,
        help=f"Inicio del backfill (AAAA-MM-DD). Por defecto: {DEFAULT_BACKFILL_DAYS} días atrás.",
    )
    parser.add_argument(
        "--end-date",
        type=date.fromisoformat,
        help=f"Fin del backfill (AAAA-MM-DD). Por defecto: hoy - {ARCHIVE_DELAY_DAYS} días.",
    )
    parser.add_argument("--no-csv", action="store_true", help="No exportar CSV a data/processed/.")
    args = parser.parse_args(argv)

    if args.backfill:
        args.end_date = args.end_date or date.today() - timedelta(days=ARCHIVE_DELAY_DAYS)
        args.start_date = args.start_date or args.end_date - timedelta(days=DEFAULT_BACKFILL_DAYS)
        if args.start_date > args.end_date:
            parser.error("--start-date debe ser anterior o igual a --end-date")
    elif args.start_date or args.end_date:
        parser.error("--start-date y --end-date solo se usan junto con --backfill")

    return args


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    args = parse_args()
    backfill = (args.start_date, args.end_date) if args.backfill else None
    # El CSV de data/processed/ refleja el pronóstico; el backfill solo va a la base de datos
    export_csv = not args.no_csv and not args.backfill

    # Código de salida != 0 para que un orquestador (cron, Airflow, CI) detecte el fallo
    sys.exit(0 if run_pipeline(export_csv=export_csv, backfill=backfill) else 1)
