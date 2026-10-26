-- Rachas de días consecutivos con lluvia (técnica "gaps and islands").
-- En una secuencia de días consecutivos, fecha - row_number() es constante:
--   01-03 - 1 = 01-02, 01-04 - 2 = 01-02, 01-05 - 3 = 01-02  → misma racha
--   01-08 - 4 = 01-04                                         → racha nueva

with rainy_days as (
    select
        location_id,
        city_name,
        date_local,
        precipitation_total_mm
    from {{ ref('fct_weather_daily') }}
    where is_rainy_day
),

islands as (
    select
        *,
        date_local
        - (row_number() over (partition by location_id order by date_local))::int as streak_group
    from rainy_days
)

select
    location_id || '-' || min(date_local) as streak_id,
    location_id,
    city_name,
    min(date_local) as streak_start_date,
    max(date_local) as streak_end_date,
    count(*) as streak_length_days,
    round(sum(precipitation_total_mm), 2) as precipitation_total_mm
from islands
group by location_id, city_name, streak_group
