"""
Load the raw CSVs from data/raw into BigQuery, so the dbt sources have
something to read when you run with --target bigquery.

Creates the dataset budget_buddy_raw (in the EU) if it doesn't exist and
replaces the four raw tables each time it runs. Every column is loaded as
STRING, the same as on DuckDB, and cleaned up by the staging models.

Load jobs are free and work in the BigQuery sandbox.

  pip install google-cloud-bigquery
  gcloud auth application-default login
  export GCP_PROJECT=your-project-id
  python scripts/load_to_bigquery.py
"""

import csv
import os
import sys
from pathlib import Path

from google.cloud import bigquery

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DATASET = "budget_buddy_raw"
LOCATION = "EU"

project = os.environ.get("GCP_PROJECT")
if not project:
    sys.exit("Set GCP_PROJECT to your Google Cloud project id first.")

client = bigquery.Client(project=project, location=LOCATION)
client.create_dataset(bigquery.Dataset(f"{project}.{DATASET}"), exists_ok=True)


def string_schema(path):
    with open(path, newline="") as f:
        header = next(csv.reader(f))
    return [bigquery.SchemaField(name, "STRING") for name in header]


def load(table, files):
    table_id = f"{project}.{DATASET}.{table}"
    for i, path in enumerate(files):
        config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,
            schema=string_schema(path),
            # First file replaces the table, any others are added to it
            write_disposition="WRITE_TRUNCATE" if i == 0 else "WRITE_APPEND",
        )
        with open(path, "rb") as f:
            client.load_table_from_file(f, table_id, job_config=config).result()
    rows = client.get_table(table_id).num_rows
    print(f"{table_id}: {rows} rows from {len(files)} file(s)")


load("users", [RAW / "users.csv"])
load("categories", [RAW / "categories.csv"])
load("budgets", [RAW / "budgets.csv"])
load("transactions", sorted(RAW.glob("transactions_*.csv")))
