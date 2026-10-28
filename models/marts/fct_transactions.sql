{{
    config(
        materialized = 'incremental',
        unique_key = 'transaction_id',
        incremental_strategy = 'delete+insert',
        on_schema_change = 'append_new_columns'
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
