select
    location_id,
    datetime_utc,
    temperature_celsius,
    relative_humidity_pct,
    precipitation_mm,
    wind_speed_kmh,
    data_source,
    data_source = 'forecast' as is_forecast,
    created_at as loaded_at
from {{ source('weather', 'fact_weather_hourly') }}
