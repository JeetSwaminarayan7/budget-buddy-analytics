with source as (

    select * from {{ source('budget_buddy', 'budgets') }}

)

select
    cast(user_id as integer)                       as user_id,
    cast(category_id as integer)                   as category_id,
    -- '2026-03' -> 2026-03-01, so it joins to transaction months
    cast(trim(month) || '-01' as date)             as budget_month,
    {{ parse_money('amount') }}                    as budget_gbp

from source
