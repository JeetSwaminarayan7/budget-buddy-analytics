with source as (

    select * from {{ source('budget_buddy', 'users') }}

)

select
    cast(id as integer)                          as user_id,
    lower(trim(username))                        as username,
    lower(trim(email))                           as email,
    {{ parse_money('monthly_budget') }}          as monthly_budget_gbp,
    {{ parse_money('savings_goal') }}            as savings_goal_gbp,
    cast(created_at as timestamp)                as created_at,
    cast(updated_at as timestamp)                as updated_at

from source
