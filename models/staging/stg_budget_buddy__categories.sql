with source as (

    select * from {{ source('budget_buddy', 'categories') }}

)

select
    cast(id as integer)           as category_id,
    cast(user_id as integer)      as user_id,
    {{ clean_text('name') }}      as category_name

from source
