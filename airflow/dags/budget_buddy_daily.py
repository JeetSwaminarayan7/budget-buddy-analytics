"""
### Budget Buddy daily build

Runs every morning at 06:00 London time:

1. **land_new_exports** moves any new export files from `data/incoming` into `data/raw`
2. **check_raw_files** fails the run early if the raw files are missing or empty
3. **dbt_build_staging** builds the staging models and runs their tests
4. **dbt_build_marts** builds everything downstream (intermediate, marts and
   the users snapshot) and runs their tests. It only runs if staging passed
5. **summarise** reads the marts and logs this month's headline numbers

Trigger it by hand with the `dbt_target` param set to `bigquery` to run the
same models on BigQuery instead of DuckDB.
"""

import csv
import os
import shutil
from datetime import timedelta
from pathlib import Path

import pendulum
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import Param, dag, task

# This file lives in <project>/airflow/dags/, so the dbt project is two
# folders up. An environment variable can point somewhere else.
PROJECT_DIR = Path(os.environ.get("BUDGET_BUDDY_DBT_DIR", Path(__file__).resolve().parents[2]))
RAW_DIR = PROJECT_DIR / "data" / "raw"
INCOMING_DIR = PROJECT_DIR / "data" / "incoming"

# dbt lives in its own virtualenv so its packages can't clash with Airflow's
DBT = os.environ.get("DBT_BIN", "dbt")
DBT_ENV = {"DBT_PROFILES_DIR": str(PROJECT_DIR)}
DBT_TARGET = "--target {{ params.dbt_target }}"


@dag(
    dag_id="budget_buddy_daily",
    schedule="0 6 * * *",
    start_date=pendulum.datetime(2026, 10, 1, tz="Europe/London"),
    catchup=False,
    # DuckDB is one file that only one process can write to at a time
    max_active_runs=1,
    default_args={
        "owner": "jeet",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
    },
    params={
        "dbt_target": Param("dev", type="string", enum=["dev", "bigquery"],
                            description="dev = DuckDB, bigquery = BigQuery"),
    },
    tags=["dbt", "budget-buddy"],
    doc_md=__doc__,
)
def budget_buddy_daily():

    @task
    def land_new_exports() -> list[str]:
        """Move files waiting in data/incoming into data/raw."""
        moved = []
        for path in sorted(INCOMING_DIR.glob("*.csv")):
            shutil.move(str(path), RAW_DIR / path.name)
            moved.append(path.name)
        print(f"Landed {len(moved)} new file(s): {moved}" if moved else "No new files today")
        return moved

    @task
    def check_raw_files() -> dict:
        """Count rows in each raw file. Fail if any are missing or empty."""
        expected = ["users.csv", "categories.csv", "budgets.csv"]
        files = [RAW_DIR / name for name in expected] + sorted(RAW_DIR.glob("transactions_*.csv"))
        if not any(f.name.startswith("transactions_") for f in files):
            raise FileNotFoundError(f"No transactions_*.csv files in {RAW_DIR}")

        counts = {}
        for f in files:
            if not f.exists():
                raise FileNotFoundError(f"Missing {f}")
            with open(f, newline="") as fh:
                counts[f.name] = sum(1 for _ in csv.reader(fh)) - 1
            if counts[f.name] <= 0:
                raise ValueError(f"{f.name} has no rows")
        print(counts)
        return counts

    # `dbt build` runs models, tests and snapshots in dependency order.
    # Splitting it by layer means bad raw data stops at staging, the marts
    # keep yesterday's good data, and the Airflow UI shows which layer broke.
    dbt_build_staging = BashOperator(
        task_id="dbt_build_staging",
        bash_command=f"{DBT} build --select path:models/staging {DBT_TARGET}",
        cwd=str(PROJECT_DIR),
        env=DBT_ENV,
        append_env=True,
    )

    dbt_build_marts = BashOperator(
        task_id="dbt_build_marts",
        bash_command=f"{DBT} build --exclude path:models/staging {DBT_TARGET}",
        cwd=str(PROJECT_DIR),
        env=DBT_ENV,
        append_env=True,
    )

    @task
    def summarise(params=None) -> dict:
        """Log the latest month's numbers from the marts (DuckDB only)."""
        if params["dbt_target"] != "dev":
            print("Summary only reads DuckDB; skipping for", params["dbt_target"])
            return {}

        import duckdb

        con = duckdb.connect(str(PROJECT_DIR / "budget_buddy.duckdb"), read_only=True)
        try:
            month, over, close, total = con.execute("""
                select budget_month,
                       count(*) filter (where budget_status = 'over'),
                       count(*) filter (where budget_status = 'close'),
                       count(*)
                from marts.mart_budget_vs_actual
                where budget_month = (select max(budget_month) from marts.mart_budget_vs_actual)
                group by budget_month
            """).fetchone()
            hit = con.execute("""
                select count(*) filter (where hit_savings_goal), count(*)
                from marts.fct_monthly_cashflow
                where transaction_month = ?
            """, [month]).fetchone()
        finally:
            con.close()

        summary = {
            "month": str(month),
            "budgets_over": over,
            "budgets_close": close,
            "budgets_total": total,
            "users_hit_savings_goal": hit[0],
            "users_active": hit[1],
        }
        print(summary)
        return summary

    land_new_exports() >> check_raw_files() >> dbt_build_staging >> dbt_build_marts >> summarise()


budget_buddy_daily()
