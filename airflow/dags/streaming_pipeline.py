from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import subprocess
import os

# Пути к скриптам в основной папке rais
PROJECT_DIR = "/home/kenan/rais"  # <-- замени на абсолютный путь к папке проекта
CLICK_GENERATOR = os.path.join(PROJECT_DIR, "/home/kenan/rais/click_generator.py")
WINDOW_AGGREGATION = os.path.join(PROJECT_DIR, "home/kenan/rais/window_aggregation.py")

def run_click_generator():
    subprocess.run(["python3", CLICK_GENERATOR])

def run_window_aggregation():
    subprocess.run(["python3", WINDOW_AGGREGATION])

with DAG(
    "streaming_pipeline",
    start_date=datetime(2026, 2, 21),
    schedule_interval="*/1 * * * *",
    catchup=False
) as dag:

    task1 = PythonOperator(
        task_id="click_generator",
        python_callable=run_click_generator
    )

    task2 = PythonOperator(
        task_id="window_aggregation",
        python_callable=run_window_aggregation
    )

    task1 >> task2
