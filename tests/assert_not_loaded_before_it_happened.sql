-- A transaction can't be loaded before the date it happened.
-- Returns any rows where it was.

select
    transaction_id,
    transaction_date,
    created_at
from {{ ref('fct_transactions') }}
where transaction_date > cast(created_at as date)
