-- Two marts work out monthly spending in different ways. If they ever
-- disagree, one of them has a bug. Returns the months that don't match.

with by_category as (

    select user_id, transaction_month, sum(spend_gbp) as spend_gbp
    from {{ ref('fct_monthly_category_spend') }}
    group by all

)

select
    c.user_id,
    c.transaction_month,
    c.spend_gbp     as cashflow_spend,
    b.spend_gbp     as category_spend
from {{ ref('fct_monthly_cashflow') }} as c
left join by_category as b
    on  c.user_id = b.user_id
    and c.transaction_month = b.transaction_month
where abs(c.spend_gbp - coalesce(b.spend_gbp, 0)) > 0.01
