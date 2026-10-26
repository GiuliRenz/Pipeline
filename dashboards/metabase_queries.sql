-- Consultas SQL nativas del dashboard de Metabase.
-- Se guardan aquí para que el dashboard sea reproducible y revisable en el repositorio.
-- {{ciudad}} es un "filtro de campo" de Metabase mapeado a fct_weather_daily.city_name.


-- 1. Pronóstico de los próximos 7 días (gráfico de líneas)
select
    date_local as fecha,
    city_name as ciudad,
    temp_min_c as minima,
    temp_max_c as maxima,
    precipitation_total_mm as lluvia_mm
from marts.fct_weather_daily
where date_local >= current_date
  and [[ {{ciudad}} and ]] true
order by fecha, ciudad;


-- 2. Cambios bruscos de temperatura entre un día y el siguiente (tabla)
select
    city_name as ciudad,
    date_local as fecha,
    temp_avg_c as temp_media,
    temp_avg_change_c as variacion_vs_dia_anterior
from marts.fct_weather_daily
where abs(temp_avg_change_c) >= 7
  and [[ {{ciudad}} and ]] true
order by abs(temp_avg_change_c) desc
limit 15;


-- 3. Días con lluvia en los últimos 30 días, por ciudad (gráfico de barras)
-- Se agrupa por ciudad: sin filtro, un count(*) total sumaría las 3 ciudades (hasta 90 "días").
select
    city_name as ciudad,
    count(*) filter (where is_rainy_day) as dias_con_lluvia
from marts.fct_weather_daily
where date_local between current_date - 30 and current_date - 1
  and [[ {{ciudad}} and ]] true
group by city_name
order by dias_con_lluvia desc;
