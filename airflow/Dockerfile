FROM apache/airflow:3.3.2-python3.12

# Dependencias del pipeline en el entorno de Airflow.
# Se fija apache-airflow para que pip no lo actualice al resolver dependencias.
RUN pip install --no-cache-dir \
    "apache-airflow==3.3.2" \
    "requests>=2.32" \
    "psycopg2-binary>=2.9.10" \
    "python-dotenv>=1.0" \
    "pydantic>=2.9"

# dbt va en un entorno virtual aparte: sus dependencias chocan con las de Airflow.
# Mismas versiones que uv.lock, para que dbt se comporte igual que en local y en CI.
RUN python -m venv /home/airflow/.dbt-venv \
    && /home/airflow/.dbt-venv/bin/pip install --no-cache-dir \
    "dbt-core==1.12.6" \
    "dbt-postgres==1.11.0"
