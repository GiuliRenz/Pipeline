"""
Verifica que todos los DAGs cargan sin errores. Se ejecuta en CI dentro de la imagen de Airflow:
un error de import o de sintaxis en un DAG se detecta antes de llegar al scheduler.
"""

import sys

from airflow.dag_processing.dagbag import DagBag

bag = DagBag("/opt/airflow/pipeline/airflow/dags")

if bag.import_errors:
    for path, error in bag.import_errors.items():
        print(f"ERROR en {path}:\n{error}")
    sys.exit(1)

if not bag.dags:
    print("ERROR: no se encontró ningún DAG")
    sys.exit(1)

for dag_id, dag in bag.dags.items():
    print(f"OK {dag_id}: {[t.task_id for t in dag.tasks]}")
