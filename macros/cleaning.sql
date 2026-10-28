{# Reusable cleaning steps for the raw app exports. #}

{# The app stored dates as text, sometimes 2026-03-05, sometimes 05/03/2026 #}
{% macro parse_flexible_date(column) -%}
    coalesce(
        try_strptime(trim({{ column }}), '%Y-%m-%d'),
        try_strptime(trim({{ column }}), '%d/%m/%Y')
    )::date
{%- endmacro %}

{# "£12.50" -> 12.50 #}
{% macro parse_money(column) -%}
    try_cast(replace(trim({{ column }}), '£', '') as decimal(12, 2))
{%- endmacro %}

{# Trim the ends and squash repeated spaces in the middle #}
{% macro clean_text(column) -%}
    regexp_replace(trim({{ column }}), '\s+', ' ', 'g')
{%- endmacro %}
