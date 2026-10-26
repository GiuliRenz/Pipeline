select
    location_id,
    city_name,
    latitude,
    longitude,
    timezone
from {{ source('weather', 'dim_locations') }}
