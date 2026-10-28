-- Adds the category name and the month to every transaction, so the
-- marts don't each repeat the same join.

with transactions as (

    select * from {{ ref('stg_budget_buddy__transactions') }}

),

categories as (

    select * from {{ ref('stg_budget_buddy__categories') }}

)

select
    t.transaction_id,
    t.user_id,
    t.transaction_date,
    {{ month_start('t.transaction_date') }}          as transaction_month,
    t.description,
    t.transaction_type,
    t.amount_gbp,
    t.signed_amount_gbp,
    t.category_id,
    coalesce(c.category_name, 'Uncategorised')        as category_name,
    t.category_id is null                             as is_uncategorised,
    t.source,
    t.created_at

from transactions as t
left join categories as c
    on t.category_id = c.category_id
