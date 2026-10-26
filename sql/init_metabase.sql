-- sql/init_metabase.sql

-- 1. Base de datos interna de Metabase: guarda usuarios, preguntas y dashboards.
--    Va separada de weather_db para no mezclar metadatos de la herramienta con los datos.
CREATE USER metabase WITH PASSWORD 'metabase_password';
CREATE DATABASE metabase OWNER metabase;

-- 2. Usuario de solo lectura con el que Metabase consulta los datos analíticos.
--    Principio de mínimo privilegio: solo puede leer el schema marts (los permisos
--    sobre las tablas los otorga dbt con la config `grants` en dbt_project.yml).
CREATE USER metabase_reader WITH PASSWORD 'reader_password';
GRANT CONNECT ON DATABASE weather_db TO metabase_reader;
