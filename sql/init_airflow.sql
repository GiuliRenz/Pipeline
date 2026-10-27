-- sql/init_airflow.sql

-- Base de datos interna de Airflow: estado de DAGs, ejecuciones y tareas.
-- Separada de weather_db por la misma razón que la de Metabase.
CREATE USER airflow WITH PASSWORD 'airflow_password';
CREATE DATABASE airflow OWNER airflow;
