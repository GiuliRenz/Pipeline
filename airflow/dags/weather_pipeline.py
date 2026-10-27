"""
### Pipeline meteorológico diario

1. **list_locations**: lee las ciudades de `dim_locations`.
2. **ingest_city**: extract → transform → load del pronóstico, una tarea por ciudad
   (dynamic task mapping): si falla una ciudad, se reintenta solo esa.
3. **dbt_build**: verifica la frescura de la fuente y reconstruye los modelos + tests.
4. **check_weather_alerts**: avisa por Telegram de lluvia intensa, calor o heladas.

Si una tarea agota sus reintentos, se envía una alerta de fallo por Telegram.
"""

from datetime import timedelta

import pendulum
from airflow.sdk import dag, get_current_context, task

PIPELINE_DIR = "/opt/airflow/pipeline"
DBT = "/home/airflow/.dbt-venv/bin/dbt"
DBT_ARGS = f"--project-dir {PIPELINE_DIR}/analytics --profiles-dir {PIPELINE_DIR}/analytics"
ALERT_DAYS_AHEAD = 3


def notify_failure(context):
    # Los imports del proyecto van dentro de las funciones: el scheduler parsea este
    # archivo cada pocos segundos y así no carga el pipeline completo en cada lectura
    from src.alerts import send_telegram_message

    ti = context["task_instance"]
    send_telegram_message(
        f"❌ Falló {ti.dag_id}.{ti.task_id} tras {ti.try_number} intentos (run: {ti.run_id})"
    )


@dag(
    dag_id="weather_pipeline",
    # 06:00 hora de Argentina, todos los días
    schedule="0 6 * * *",
    start_date=pendulum.datetime(2026, 10, 1, tz="America/Argentina/Buenos_Aires"),
    # El pronóstico siempre trae "los últimos 7 días + los próximos 7": no hace falta
    # recuperar ejecuciones pasadas; el histórico se carga con `main.py --backfill`
    catchup=False,
    max_active_runs=1,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "on_failure_callback": notify_failure,
    },
    tags=["weather", "etl", "dbt"],
    doc_md=__doc__,
)
def weather_pipeline():
    @task
    def list_locations() -> list[dict]:
        from main import get_locations

        return get_locations()

    @task(map_index_template="{{ city }}")
    def ingest_city(location: dict) -> int:
        import os

        from main import process_city

        # Nombre legible de cada tarea mapeada en la interfaz (en vez de 0, 1, 2)
        get_current_context()["city"] = location["city_name"]
        # Los archivos de data/raw y data/quarantine se escriben en el proyecto montado
        os.chdir(PIPELINE_DIR)
        return process_city(location, export_csv=False)

    @task.bash
    def dbt_build() -> str:
        # La frescura va primero: si la ingesta no cargó nada nuevo, falla antes de construir
        return f"{DBT} source freshness {DBT_ARGS} && {DBT} build {DBT_ARGS}"

    @task
    def check_weather_alerts() -> int:
        from src.alerts import build_weather_alerts, get_upcoming_weather, send_telegram_message

        alerts = build_weather_alerts(get_upcoming_weather(days_ahead=ALERT_DAYS_AHEAD))
        if alerts:
            send_telegram_message("⚠️ Alertas meteorológicas\n\n" + "\n".join(alerts))
        return len(alerts)

    ingested = ingest_city.expand(location=list_locations())
    ingested >> dbt_build() >> check_weather_alerts()


weather_pipeline()
