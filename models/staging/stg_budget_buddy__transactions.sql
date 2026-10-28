with source as (

    select * from {{ source('budget_buddy', 'transactions') }}

),

cleaned as (

    select
        cast(id as integer)                               as transaction_id,
        cast(user_id as integer)                          as user_id,
        {{ parse_flexible_date('date') }}                 as transaction_date,
        upper({{ clean_text('description') }})            as description,
        {{ parse_money('amount') }}                       as amount_gbp,
        lower(trim(type))                                 as transaction_type,
        try_cast(nullif(trim(category_id), '') as integer) as category_id,
        lower(trim(source))                               as source,
        cast(created_at as timestamp)                     as created_at

    from source

),

-- When someone uploads the same PDF statement twice, every row comes in
-- again with a new id. Keep the first copy of each.
deduplicated as (

    select
        *,
        row_number() over (
            partition by user_id, transaction_date, description, amount_gbp, transaction_type
            order by transaction_id
        ) as copy_number

    from cleaned

)

select
    transaction_id,
    user_id,
    transaction_date,
    description,
    amount_gbp,
    transaction_type,
    -- Money in is positive, money out is negative
    case when transaction_type = 'credit' then amount_gbp else -amount_gbp end as signed_amount_gbp,
    category_id,
    source,
    created_at

from deduplicated
where copy_number = 1
