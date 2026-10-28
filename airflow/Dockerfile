FROM apache/airflow:3.3.2-python3.12

# duckdb goes into Airflow's own environment for the summarise task.
# Pinning apache-airflow stops pip from upgrading it by accident.
RUN pip install --no-cache-dir "apache-airflow==3.3.2" duckdb

# dbt gets its own virtualenv. dbt and Airflow both pull in a lot of
# packages, and keeping them apart means one can't break the other.
COPY requirements.txt /tmp/requirements-dbt.txt
RUN python -m venv /home/airflow/dbt-venv \
 && /home/airflow/dbt-venv/bin/pip install --no-cache-dir -r /tmp/requirements-dbt.txt

ENV DBT_BIN=/home/airflow/dbt-venv/bin/dbt
