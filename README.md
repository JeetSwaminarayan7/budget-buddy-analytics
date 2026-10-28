# Budget Buddy analytics (dbt)

A dbt project that turns raw exports from [Budget Buddy](https://github.com/JeetSwaminarayan7/budget-buddy), my personal finance app, into clean tables for reporting: monthly spending by category, budget against actual, and cash flow against savings goals.

It runs on DuckDB, a database that lives in one file, so there's nothing to install beyond Python and nothing to pay for. The same models would run on Snowflake or BigQuery with a different profile.

## The data

`data/raw/` holds fake exports for 25 users, January to September 2026: about 7,400 transactions plus users, categories and monthly budgets. `scripts/generate_raw_data.py` makes them, and makes them messy on purpose, because that's what the staging layer is for:

- dates in two formats, `2026-03-05` and `05/03/2026`
- descriptions like `"  waitrose "` and `Tesco Stores`
- transaction types like `" DEBIT "` and `Credit`
- some amounts written as `£12.50`
- about 1% of transactions loaded twice, as if someone uploaded the same bank statement again
- about 12% with no category

`data/incoming/` holds October's transactions, which aren't loaded yet. They're for the incremental demo below.

## How it's built

```
sources (CSV files)            staging (views)                 intermediate          marts (tables)
───────────────────            ───────────────                 ────────────          ──────────────
users        ──────────▶  stg_budget_buddy__users  ───────────────────────────────▶ dim_users
categories   ──────────▶  stg_budget_buddy__categories ──┐                           fct_monthly_cashflow
transactions ──────────▶  stg_budget_buddy__transactions ┴─▶ int_transactions_ ───▶ fct_transactions (incremental)
budgets      ──────────▶  stg_budget_buddy__budgets  ─┐       enriched                  │
                                                      │                                 ▼
                                                      └──────────────────────────▶ fct_monthly_category_spend
                                                                                        │
                                                                                        ▼
                                                                                  mart_budget_vs_actual

snapshots: users_snapshot (history of every user's settings)
```

**Sources** (`models/staging/_sources.yml`) point dbt at the raw CSV files. Everything is read as text, like a raw landing zone, and the transactions source uses a wildcard so new export files get picked up automatically.

**Staging** has one model per source table, and only cleans: fixes types, trims text, parses both date formats, strips pound signs, and removes the duplicate rows from re-uploaded statements. No business logic.

**Intermediate** joins each transaction to its category name and works out its month, once, so the marts don't each repeat that join.

**Marts** are the tables you'd point a dashboard at:

| Model | One row per | What it answers |
|---|---|---|
| `fct_transactions` | transaction | Every clean transaction. Built incrementally |
| `fct_monthly_category_spend` | user, month, category | How much did each user spend on groceries in March? |
| `fct_monthly_cashflow` | user, month | Income, spending, what's left, and did they hit their savings goal? |
| `mart_budget_vs_actual` | user, month, budgeted category | Were they over, close to (90%+) or under each budget? |
| `dim_users` | user | Current settings plus first and last transaction and how much is uncategorised |

**Macros** (`macros/cleaning.sql`) hold the cleaning steps used in more than one model: `parse_flexible_date`, `parse_money` and `clean_text`. `generate_schema_name.sql` makes models land in schemas called `staging`, `intermediate` and `marts` instead of dbt's default `main_staging`.

## Tests

`dbt build` runs 48 data tests and 1 unit test alongside the models. A failed test stops anything downstream from building.

- **Built-in tests** on columns: `unique`, `not_null`, `accepted_values` (types must be `debit` or `credit`) and `relationships` (every transaction's user must exist).
- **Custom generic tests** in `tests/generic/`: `is_positive` for amounts and budgets, and `unique_combination` for tables whose key is several columns, like user + month + category.
- **Singular tests** in `tests/`: one checks the two marts that both work out monthly spending agree with each other to the penny; the other checks no transaction was loaded before the date it happened.
- **A unit test** in `models/marts/_marts.yml` feeds `mart_budget_vs_actual` four made-up rows (£89.99, £90, £100.01 and nothing spent, against £100 budgets) and checks they come out `under`, `close`, `over` and `under`. It tests the logic without touching the real data.

## Running it

You need Python 3.10 or newer.

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

dbt debug      # checks dbt can find the project and the database
dbt build      # builds every model and runs every test
```

It should finish with `PASS=60 WARN=0 ERROR=0`.

To look at the results, open the database in DuckDB's own UI, or with Python:

```bash
python -c "import duckdb; print(duckdb.connect('budget_buddy.duckdb').sql('select * from marts.mart_budget_vs_actual limit 10'))"
```

And to see the documentation site, with every model, column description and a clickable lineage graph:

```bash
dbt docs generate
dbt docs serve     # opens it in your browser
```

## Incremental models and snapshots

These two only make sense once data changes, so there's a script that pretends a day has passed:

```bash
python scripts/simulate_new_day.py
dbt snapshot
dbt build
```

The script moves October's 832 transactions into `data/raw/` and changes two users' monthly budgets (user 3 from £2,000 to £2,500, user 7 from £1,000 to £650).

**Incremental:** `fct_transactions` doesn't rebuild. It finds the newest `created_at` it already has and only adds rows loaded after that, going from 7,294 rows to 8,117. With millions of rows that's the difference between seconds and hours. `dbt build --full-refresh` rebuilds it from scratch, and gives exactly the same rows.

**Snapshot:** `users_snapshot` keeps every version of each user's settings (a Type 2 slowly changing dimension). After the run, user 3 has two rows: £2,000 valid until 20 October, and £2,500 valid from then with `dbt_valid_to` empty. You can see what anyone's budget was on any date.

```bash
python -c "import duckdb; print(duckdb.connect('budget_buddy.duckdb').sql('select user_id, monthly_budget_gbp, dbt_valid_from, dbt_valid_to from snapshots.users_snapshot where user_id in (3, 7) order by 1, 3'))"
```

To put the data back how it was:

```bash
git checkout -- data/ && git clean -fd data/
rm budget_buddy.duckdb
```

## CI

`.github/workflows/dbt.yml` runs on every push: `dbt build`, then the new-day script, then `dbt snapshot` and `dbt build` again, so the incremental path and the snapshot are tested as well as a fresh build.

## Layout

```
├── data/
│   ├── raw/                 # landed exports (sources read these)
│   └── incoming/            # October, not landed yet
├── macros/
├── models/
│   ├── staging/             # _sources.yml, _staging.yml, stg_*.sql
│   ├── intermediate/
│   └── marts/               # _marts.yml has the unit test
├── snapshots/
├── tests/
│   └── generic/
├── scripts/                 # data generator and new-day simulator
├── dbt_project.yml
└── profiles.yml             # DuckDB connection, kept in the repo
```
