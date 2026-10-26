-- Dos rachas de la misma ciudad deben estar separadas por al menos un día seco;
-- si una empieza justo al día siguiente de otra, la lógica de agrupación falló.
with ordered as (
    select
        *,
        lag(streak_end_date) over (
            partition by location_id order by streak_start_date
        ) as previous_streak_end
    from {{ ref('fct_rain_streaks') }}
)

select *
from ordered
where streak_start_date - previous_streak_end <= 1
