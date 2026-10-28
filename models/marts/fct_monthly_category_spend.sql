-- How much each user spent in each category each month. Money out only.

select
    user_id,
    transaction_month,
    category_id,
    category_name,
    count(*)                    as transaction_count,
    sum(amount_gbp)             as spend_gbp

from {{ ref('fct_transactions') }}
where transaction_type = 'debit'
group by user_id, transaction_month, category_id, category_name
