-- sql/init_db.sql

-- 1. Crear tabla de dimensión (Ubicaciones)
CREATE TABLE IF NOT EXISTS dim_locations (
    location_id SERIAL PRIMARY KEY,
    city_name VARCHAR(100) NOT NULL UNIQUE,
    latitude DECIMAL(8, 5) NOT NULL,
    longitude DECIMAL(8, 5) NOT NULL,
    timezone VARCHAR(50) NOT NULL
);

-- 2. Crear tabla de hechos (Mediciones por hora)
CREATE TABLE IF NOT EXISTS fact_weather_hourly (
    measurement_id BIGSERIAL PRIMARY KEY,
    location_id INT NOT NULL REFERENCES dim_locations(location_id),
    datetime_utc TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    temperature_celsius DECIMAL(4, 2),
    relative_humidity_pct INT,
    precipitation_mm DECIMAL(5, 2),
    wind_speed_kmh DECIMAL(5, 2),
    -- 'archive' = dato observado (Archive API), 'forecast' = pronóstico (Forecast API)
    data_source VARCHAR(10) NOT NULL DEFAULT 'forecast',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    -- Evita duplicar mediciones si el ETL se ejecuta varias veces
    CONSTRAINT unique_location_datetime UNIQUE (location_id, datetime_utc),
    -- Segunda línea de defensa: los mismos rangos que valida src/schemas.py
    CONSTRAINT chk_temperature CHECK (temperature_celsius BETWEEN -90 AND 60),
    CONSTRAINT chk_humidity CHECK (relative_humidity_pct BETWEEN 0 AND 100),
    CONSTRAINT chk_precipitation CHECK (precipitation_mm BETWEEN 0 AND 500),
    CONSTRAINT chk_wind_speed CHECK (wind_speed_kmh BETWEEN 0 AND 400),
    CONSTRAINT chk_data_source CHECK (data_source IN ('forecast', 'archive'))
);

-- 3. Inserción inicial de ciudades para monitorear
INSERT INTO dim_locations (city_name, latitude, longitude, timezone)
VALUES 
    ('Buenos Aires', -34.6037, -58.3816, 'America/Argentina/Buenos_Aires'),
    ('Bahía Blanca', -38.7183, -62.2663, 'America/Argentina/Buenos_Aires'),
    ('Cordoba', -31.4135, -64.1810, 'America/Argentina/Buenos_Aires')
ON CONFLICT (city_name) DO NOTHING;