with hourly as (
    select * from {{ ref('int_weather__hourly_local') }}
),

daily as (
    select
        location_id,
        city_name,
        date_local,
        round(avg(temperature_celsius), 2) as temp_avg_c,
        min(temperature_celsius) as temp_min_c,
        max(temperature_celsius) as temp_max_c,
        round(sum(precipitation_mm), 2) as precipitation_total_mm,
        round(avg(relative_humidity_pct), 1) as humidity_avg_pct,
        max(wind_speed_kmh) as wind_max_kmh,
        count(*) as hours_recorded,
        bool_or(is_forecast) as includes_forecast
    from hourly
    group by location_id, city_name, date_local
),

with_previous_day as (
    select
        *,
        lag(date_local) over by_location as previous_date,
        lag(temp_avg_c) over by_location as previous_temp_avg_c
    from daily
    window by_location as (partition by location_id order by date_local)
)

select
    location_id || '-' || date_local as location_day_id,
    location_id,
    city_name,
    date_local,
    temp_avg_c,
    temp_min_c,
    temp_max_c,
    temp_max_c - temp_min_c as temp_range_c,
    -- Solo se compara con el día calendario anterior: si falta un día, la variación queda nula
    case
        when date_local - previous_date = 1 then temp_avg_c - previous_temp_avg_c
    end as temp_avg_change_c,
    precipitation_total_mm,
    coalesce(precipitation_total_mm, 0) >= {{ var('rainy_day_threshold_mm') }} as is_rainy_day,
    humidity_avg_pct,
    wind_max_kmh,
    hours_recorded,
    -- Las ciudades monitoreadas no tienen horario de verano, por lo que un día completo tiene 24 h
    hours_recorded = 24 as is_complete_day,
    includes_forecast
from with_previous_day
