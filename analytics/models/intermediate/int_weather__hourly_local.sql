-- Convierte cada medición a la hora local de su ciudad.
-- Es necesario para agregar por día: un "día" en Córdoba no empieza a las 00:00 UTC.

with hourly as (
    select * from {{ ref('stg_weather__hourly') }}
),

locations as (
    select * from {{ ref('stg_weather__locations') }}
),

localized as (
    select
        hourly.location_id,
        locations.city_name,
        hourly.datetime_utc,
        (hourly.datetime_utc at time zone 'UTC') at time zone locations.timezone as datetime_local,
        hourly.temperature_celsius,
        hourly.relative_humidity_pct,
        hourly.precipitation_mm,
        hourly.wind_speed_kmh,
        hourly.is_forecast
    from hourly
    inner join locations
        on hourly.location_id = locations.location_id
)

select
    *,
    datetime_local::date as date_local
from localized
