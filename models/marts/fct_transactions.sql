{#
    incremental_strategy: BigQuery does incremental loads with MERGE.
    DuckDB deletes the matching rows and inserts the new ones.

    partition_by and cluster_by are only set on BigQuery.
    Partitioning by month means a query for March reads March's data, not
    the whole table, so it's faster and you pay for less. Clustering by
    user keeps each user's rows next to each other.
#}
{{
    config(
        materialized = 'incremental',
        unique_key = 'transaction_id',
        on_schema_change = 'append_new_columns',
        incremental_strategy = 'merge' if target.type == 'bigquery' else 'delete+insert',
        partition_by = {'field': 'transaction_date', 'data_type': 'date', 'granularity': 'month'} if target.type == 'bigquery' else none,
        cluster_by = ['user_id'] if target.type == 'bigquery' else none
    )
}}

-- Incremental: the first run builds the whole table. After that, each run
-- only adds transactions loaded since the newest one already in the table,
-- instead of rebuilding everything. `dbt build --full-refresh` rebuilds it.

select *
from {{ ref('int_transactions_enriched') }}

{% if is_incremental() %}
where created_at > (select max(created_at) from {{ this }})
{% endif %}
