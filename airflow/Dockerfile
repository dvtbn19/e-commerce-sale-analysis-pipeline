FROM apache/airflow:3.3.1-python3.12

COPY airflow/requirements.txt /requirements.txt

RUN pip install --no-cache-dir \
    "apache-airflow==3.3.1" \
    -r /requirements.txt

COPY --chown=airflow:root airflow/dags /opt/airflow/dags

COPY --chown=airflow:root services /opt/project/services

COPY --chown=airflow:root dbt/ecommerce /opt/project/dbt/ecommerce

COPY --chown=airflow:root data/raw/ecommerce /opt/project/data/raw/ecommerce

ENV PYTHONPATH="/opt/project"