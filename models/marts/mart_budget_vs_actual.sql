-- For every budget a user set, how much they actually spent against it.

with budgets as (

    select * from {{ ref('stg_budget_buddy__budgets') }}

),

categories as (

    select * from {{ ref('stg_budget_buddy__categories') }}

),

spend as (

    select * from {{ ref('fct_monthly_category_spend') }}

),

joined as (

    select
        b.user_id,
        b.budget_month,
        b.category_id,
        c.category_name,
        b.budget_gbp,
        -- No spending that month counts as zero, not missing
        coalesce(s.spend_gbp, 0)            as actual_gbp

    from budgets as b
    inner join categories as c
        on b.category_id = c.category_id
    left join spend as s
        on  b.user_id = s.user_id
        and b.category_id = s.category_id
        and b.budget_month = s.transaction_month

)

select
    *,
    budget_gbp - actual_gbp                                 as remaining_gbp,
    round(actual_gbp / budget_gbp * 100, 1)                 as pct_used,
    case
        when actual_gbp > budget_gbp        then 'over'
        when actual_gbp >= budget_gbp * 0.9 then 'close'
        else 'under'
    end                                                     as budget_status

from joined
