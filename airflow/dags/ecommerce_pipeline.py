from datetime import datetime, timedelta
import subprocess
import os
import redis

from airflow.sdk import dag, task

from services.ingestion.loader import ingest_amazon_sales


DBT_PROJECT_DIR = "/opt/project/dbt/ecommerce"


@dag(
    dag_id="ecommerce_pipeline",
    description="Ingest Amazon sales data, run dbt models, and validate data quality.",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["ecommerce", "ingestion", "dbt"],
    default_args={
        "retries": 1,
        "retry_delay": timedelta(minutes=1),
    },
)
def ecommerce_pipeline():

    @task(task_id="ingest_amazon_sales")
    def ingest():
        result = ingest_amazon_sales()

        print("Ingestion result:")
        print(result)

        return result

    @task(task_id="dbt_run")
    def run_dbt():

        command = [
            "dbt",
            "run",
            "--profiles-dir",
            ".",
        ]

        print(
            "Running:",
            " ".join(command),
        )

        subprocess.run(
            command,
            cwd=DBT_PROJECT_DIR,
            check=True,
        )

    @task(task_id="dbt_test")
    def test_dbt():

        command = [
            "dbt",
            "test",
            "--profiles-dir",
            ".",
        ]

        print(
            "Running:",
            " ".join(command),
        )

        subprocess.run(
            command,
            cwd=DBT_PROJECT_DIR,
            check=True,
        )


    @task(task_id="invalidate_cache")
    def invalidate_cache():
        try:
            client = redis.Redis(
                host=os.getenv(
                    "REDIS_HOST",
                    "host.docker.internal",
                ),
                port=int(
                    os.getenv(
                        "REDIS_PORT",
                        "6379",
                    )
                ),
                db=int(
                    os.getenv(
                        "REDIS_DB",
                        "0",
                    )
                ),
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1,
            )

            fixed_keys = [
                "ecommerce:sales:summary:v1",
                "ecommerce:sales:categories:v1",
            ]

            keys_to_delete = list(fixed_keys)

            for key in client.scan_iter(
                match="ecommerce:sales:list:v1:*",
                count=100,
            ):
                keys_to_delete.append(key)

            if keys_to_delete:
                deleted = client.delete(*keys_to_delete)
            else:
                deleted = 0
            print(
                f"Cache invalidation completed. "
                f"Deleted {deleted} key(s)."
            )

        except redis.RedisError as exc:
            print(
                "Redis unavailable. "
                f"Skipping cache invalidation: {exc}"
            )

    # Define the task dependencies
    ingestion_task = ingest()

    dbt_run_task = run_dbt()

    dbt_test_task = test_dbt()

    cache_invalidation_task = invalidate_cache()

    ingestion_task >> dbt_run_task >> dbt_test_task >> cache_invalidation_task


ecommerce_pipeline()