-- One row per user with their current settings and a summary of activity.

with users as (

    select * from {{ ref('stg_budget_buddy__users') }}

),

activity as (

    select
        user_id,
        min(transaction_date)                                       as first_transaction_date,
        max(transaction_date)                                       as last_transaction_date,
        count(*)                                                    as transaction_count,
        round(avg(case when is_uncategorised then 1 else 0 end) * 100, 1)
                                                                    as pct_uncategorised

    from {{ ref('fct_transactions') }}
    group by user_id

)

select
    u.user_id,
    u.username,
    u.email,
    u.monthly_budget_gbp,
    u.savings_goal_gbp,
    u.created_at                       as signed_up_at,
    a.first_transaction_date,
    a.last_transaction_date,
    coalesce(a.transaction_count, 0)   as transaction_count,
    a.pct_uncategorised

from users as u
left join activity as a
    on u.user_id = a.user_id
