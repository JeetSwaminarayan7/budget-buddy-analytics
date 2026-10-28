"""
Generate fake raw exports from the Budget Buddy app database.

The data is deliberately messy, the way real app exports are, so the
staging models have something to clean up:
  - dates in two formats (2026-03-05 and 05/03/2026)
  - descriptions with random capitalisation and extra spaces
  - transaction types like "DEBIT " and "Credit"
  - some amounts with a pound sign
  - about 2% of transactions loaded twice (a PDF statement uploaded again)
  - about 12% of transactions with no category

Writes:
  data/raw/users.csv
  data/raw/categories.csv
  data/raw/budgets.csv
  data/raw/transactions_2026_q1_q3.csv   Jan to Sep 2026
  data/incoming/transactions_2026_10.csv October, for the incremental demo

Run from the project root:  python scripts/generate_raw_data.py
"""

import csv
import datetime as dt
import random
from pathlib import Path

random.seed(42)

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
INCOMING = ROOT / "data" / "incoming"

N_USERS = 25

# Same default categories the Budget Buddy app creates for every new user
CATEGORIES = [
    "Groceries", "Transport", "Dining", "Entertainment", "Utilities",
    "Housing", "Healthcare", "Shopping", "Education", "Income",
]

# (category, merchants, low, high, times per month)
SPENDING = [
    ("Groceries", ["TESCO STORES", "SAINSBURYS", "LIDL GB", "ALDI STORES", "WAITROSE"], 8, 85, 6),
    ("Transport", ["TFL TRAVEL CHARGE", "UBER TRIP", "TRAINLINE", "SHELL PETROL"], 2.8, 45, 10),
    ("Dining", ["PRET A MANGER", "NANDOS", "DELIVEROO", "COSTA COFFEE", "WAGAMAMA"], 4, 40, 5),
    ("Entertainment", ["NETFLIX.COM", "SPOTIFY UK", "VUE CINEMAS", "STEAM PURCHASE"], 5, 30, 2),
    ("Utilities", ["THAMES WATER", "OCTOPUS ENERGY", "VIRGIN MEDIA", "EE LIMITED"], 20, 90, 3),
    ("Shopping", ["AMAZON.CO.UK", "ARGOS", "PRIMARK", "JOHN LEWIS", "BOOTS"], 6, 120, 3),
    ("Healthcare", ["BOOTS PHARMACY", "SUPERDRUG", "NHS PRESCRIPTION"], 5, 25, 1),
    ("Education", ["UDEMY", "WATERSTONES", "COURSERA"], 10, 60, 0.5),
]


def messy_case(text):
    style = random.random()
    if style < 0.5:
        return text
    if style < 0.75:
        return text.title()
    return text.lower()


def messy_spaces(text):
    if random.random() < 0.3:
        text = text.replace(" ", "  ", 1)
    if random.random() < 0.2:
        text = "  " + text + " "
    return text


def messy_date(d):
    return d.strftime("%d/%m/%Y") if random.random() < 0.3 else d.isoformat()


def messy_type(t):
    return random.choice([t, t, t, t.upper(), t.title(), f" {t.upper()} "])


def messy_amount(a):
    return f"£{a:.2f}" if random.random() < 0.1 else f"{a:.2f}"


def ts(d):
    return d.strftime("%Y-%m-%d %H:%M:%S")


def month_days(year, month, last_day=None):
    start = dt.date(year, month, 1)
    nxt = dt.date(year + (month == 12), month % 12 + 1, 1)
    end = nxt - dt.timedelta(days=1)
    if last_day:
        end = min(end, dt.date(year, month, last_day))
    return start, end


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    INCOMING.mkdir(parents=True, exist_ok=True)

    users, categories, budgets = [], [], []
    salaries = {}  # user_id -> monthly salary, fixed for the year
    cat_ids = {}  # (user_id, name) -> category_id
    cat_id = 1

    for uid in range(1, N_USERS + 1):
        created = dt.datetime(2025, random.randint(6, 12), random.randint(1, 28), random.randint(8, 22))
        users.append({
            "id": uid,
            "username": messy_spaces(f"user{uid:02d}"),
            "email": f"User{uid:02d}@Example.com" if random.random() < 0.3 else f"user{uid:02d}@example.com",
            "monthly_budget": random.choice([800, 1000, 1200, 1500, 2000]),
            "savings_goal": random.choice([200, 300, 500, 750]),
            "created_at": ts(created),
            "updated_at": ts(created),
        })
        salaries[uid] = random.choice([1900, 2200, 2600, 3100])
        for name in CATEGORIES:
            categories.append({"id": cat_id, "user_id": uid, "name": messy_spaces(name)})
            cat_ids[(uid, name)] = cat_id
            cat_id += 1

    def build_transactions(months, start_id):
        rows = []
        tid = start_id
        for (year, month, last_day) in months:
            first, last = month_days(year, month, last_day)
            span = (last - first).days
            for u in users:
                uid = u["id"]
                salary = salaries[uid]
                planned = [("Income", "SALARY ACME LTD", salary, salary, 1, "credit"),
                           ("Housing", "RENT PAYMENT", 650, 1100, 1, "debit")]
                planned += [(c, m, lo, hi, n, "debit") for (c, m, lo, hi, n) in SPENDING]

                for (cat, merchants, lo, hi, per_month, ttype) in planned:
                    n = int(per_month) + (1 if random.random() < per_month % 1 else 0)
                    n = max(0, n + random.randint(-1, 1)) if per_month >= 2 else n
                    for _ in range(n):
                        day = first + dt.timedelta(days=random.randint(0, span))
                        merchant = merchants if isinstance(merchants, str) else random.choice(merchants)
                        amount = round(random.uniform(lo, hi), 2)
                        source = random.choice(["pdf", "pdf", "manual"])
                        created = dt.datetime.combine(
                            last if source == "pdf" else day,
                            dt.time(random.randint(7, 23), random.randint(0, 59)),
                        )
                        category = "" if (cat != "Income" and random.random() < 0.12) else cat_ids[(uid, cat)]
                        row = {
                            "id": tid,
                            "user_id": uid,
                            "date": messy_date(day),
                            "description": messy_spaces(messy_case(merchant)),
                            "amount": messy_amount(amount),
                            "type": messy_type(ttype),
                            "category_id": category,
                            "source": source,
                            "created_at": ts(created),
                        }
                        rows.append(row)
                        tid += 1
                        # Same statement uploaded twice: identical row, new id, later load time
                        if source == "pdf" and random.random() < 0.02:
                            dup = dict(row, id=tid, created_at=ts(created + dt.timedelta(hours=3)))
                            rows.append(dup)
                            tid += 1
        rows.sort(key=lambda r: r["id"])
        return rows, tid

    history, next_id = build_transactions([(2026, m, None) for m in range(1, 10)], 1)
    october, _ = build_transactions([(2026, 10, 27)], next_id)

    for u in users:
        for month in range(1, 11):
            for cat in random.sample(["Groceries", "Transport", "Dining", "Entertainment", "Shopping"], 3):
                budgets.append({
                    "user_id": u["id"],
                    "category_id": cat_ids[(u["id"], cat)],
                    "amount": random.choice([50, 75, 100, 150, 200, 300]),
                    "month": f"2026-{month:02d}",
                })

    def write(path, rows):
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"{path.relative_to(ROOT)}: {len(rows)} rows")

    write(RAW / "users.csv", users)
    write(RAW / "categories.csv", categories)
    write(RAW / "budgets.csv", budgets)
    write(RAW / "transactions_2026_q1_q3.csv", history)
    write(INCOMING / "transactions_2026_10.csv", october)


if __name__ == "__main__":
    main()
