-- Money in, money out and what's left, per user per month, checked
-- against the savings goal they set.

with monthly as (

    select
        user_id,
        transaction_month,
        sum(case when transaction_type = 'credit' then amount_gbp else 0 end) as income_gbp,
        sum(case when transaction_type = 'debit'  then amount_gbp else 0 end) as spend_gbp,
        sum(signed_amount_gbp)                                                 as net_gbp

    from {{ ref('fct_transactions') }}
    group by all

),

users as (

    select user_id, savings_goal_gbp from {{ ref('stg_budget_buddy__users') }}

)

select
    m.user_id,
    m.transaction_month,
    m.income_gbp,
    m.spend_gbp,
    m.net_gbp,
    u.savings_goal_gbp,
    m.net_gbp >= u.savings_goal_gbp                         as hit_savings_goal,
    round(m.net_gbp / nullif(m.income_gbp, 0) * 100, 1)     as savings_rate_pct

from monthly as m
inner join users as u
    on m.user_id = u.user_id
