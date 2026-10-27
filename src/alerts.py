import logging
import os

import requests
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

from src.load import get_db_connection

load_dotenv()

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"

# Umbrales de alerta meteorológica (por día y ciudad)
HEAVY_RAIN_MM = 20.0
HEAT_CELSIUS = 35.0
FROST_CELSIUS = 0.0

UPCOMING_WEATHER_QUERY = """
    SELECT city_name, date_local, temp_min_c, temp_max_c, precipitation_total_mm
    FROM marts.fct_weather_daily
    WHERE date_local BETWEEN current_date AND current_date + %s
    ORDER BY date_local, city_name;
"""


def get_upcoming_weather(days_ahead: int) -> list[dict]:
    """
    Lee de la capa gold los próximos días de pronóstico por ciudad.
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(UPCOMING_WEATHER_QUERY, (days_ahead,))
            return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def build_weather_alerts(days: list[dict]) -> list[str]:
    """
    Recibe días de pronóstico (filas de fct_weather_daily) y devuelve un mensaje
    por cada condición extrema: lluvia intensa, calor o helada.
    """
    alerts = []
    for day in days:
        place = f"{day['city_name']} ({day['date_local']:%d/%m})"
        rain = day["precipitation_total_mm"]
        t_max = day["temp_max_c"]
        t_min = day["temp_min_c"]

        if rain is not None and rain >= HEAVY_RAIN_MM:
            alerts.append(f"🌧 Lluvia intensa en {place}: {rain} mm")
        if t_max is not None and t_max >= HEAT_CELSIUS:
            alerts.append(f"🔥 Calor extremo en {place}: máxima de {t_max} °C")
        if t_min is not None and t_min <= FROST_CELSIUS:
            alerts.append(f"❄️ Helada en {place}: mínima de {t_min} °C")
    return alerts


def send_telegram_message(text: str) -> bool:
    """
    Envía un mensaje al chat de Telegram configurado. Si faltan las credenciales
    (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID) solo lo registra en el log: las alertas
    son opcionales y su ausencia no debe romper el pipeline.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        logger.warning(f"Telegram no configurado; alerta no enviada: {text}")
        return False

    response = requests.post(
        TELEGRAM_API_URL.format(token=token),
        json={"chat_id": chat_id, "text": text},
        timeout=10,
    )
    response.raise_for_status()
    logger.info("Alerta enviada a Telegram.")
    return True
