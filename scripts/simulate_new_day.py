"""
Pretend a day has passed in the app, so you can watch the incremental
model and the snapshot do their jobs.

  1. Moves October's transactions from data/incoming into data/raw,
     as if a new export had landed.
  2. Changes the monthly budget for users 3 and 7 and bumps their
     updated_at, as if they'd edited their settings.

Then run:  dbt snapshot && dbt build
To undo:   git checkout -- data/ && git clean -fd data/
"""

import csv
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
src = ROOT / "data" / "incoming" / "transactions_2026_10.csv"
dst = ROOT / "data" / "raw" / "transactions_2026_10.csv"

if src.exists():
    shutil.move(src, dst)
    print(f"Moved {src.name} into data/raw")
else:
    print("October transactions already in data/raw")

users_path = ROOT / "data" / "raw" / "users.csv"
with open(users_path, newline="") as f:
    rows = list(csv.DictReader(f))

changes = {"3": "2500", "7": "650"}
for row in rows:
    if row["id"] in changes and row["monthly_budget"] != changes[row["id"]]:
        print(f"User {row['id']}: monthly_budget {row['monthly_budget']} -> {changes[row['id']]}")
        row["monthly_budget"] = changes[row["id"]]
        row["updated_at"] = "2026-10-20 18:30:00"

with open(users_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
