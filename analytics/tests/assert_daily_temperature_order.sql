-- Falla si algún día tiene temperatura mínima > media o media > máxima.
select *
from {{ ref('fct_weather_daily') }}
where temp_min_c > temp_avg_c
   or temp_avg_c > temp_max_c
