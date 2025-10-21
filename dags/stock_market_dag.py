# dags/stock_market_dag.py

from __future__ import annotations

import pendulum
from airflow.models.dag import DAG
from airflow.operators.python import PythonOperator

from scripts.tasks import run_stock_pipeline

with DAG(
    dag_id="stock_market_data_pipeline",
    start_date=pendulum.datetime(2025, 10, 15, tz="UTC"), 
    schedule="@daily", 
    catchup=False, 
    tags=["stock_market", "api"],
) as dag:

    run_etl_task = PythonOperator(
        task_id="run_full_stock_etl",
        python_callable=run_stock_pipeline,
    )