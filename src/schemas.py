from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class WeatherRecord(BaseModel):
    """
    Contrato de datos de una medición horaria antes de cargarla en fact_weather_hourly.
    Los rangos representan límites físicamente plausibles: un valor fuera de ellos
    indica un dato corrupto de la API, no un evento meteorológico real.
    """

    model_config = ConfigDict(extra="forbid")

    location_id: int = Field(gt=0)
    datetime_utc: datetime
    # Récords mundiales aprox.: -89.2 °C (Vostok) y 56.7 °C (Death Valley)
    temperature_celsius: float | None = Field(default=None, ge=-90, le=60)
    relative_humidity_pct: int | None = Field(default=None, ge=0, le=100)
    precipitation_mm: float | None = Field(default=None, ge=0, le=500)
    wind_speed_kmh: float | None = Field(default=None, ge=0, le=400)
    data_source: Literal["forecast", "archive"]

    @model_validator(mode="after")
    def at_least_one_measure(self) -> "WeatherRecord":
        # Una fila sin ninguna medición no aporta información y solo ensucia la tabla de hechos
        measures = (
            self.temperature_celsius,
            self.relative_humidity_pct,
            self.precipitation_mm,
            self.wind_speed_kmh,
        )
        if all(m is None for m in measures):
            raise ValueError("el registro no contiene ninguna medición")
        return self
