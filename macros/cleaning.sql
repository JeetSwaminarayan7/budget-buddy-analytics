{#
    Reusable cleaning steps for the raw app exports.

    DuckDB and BigQuery spell some of these differently, so each macro
    uses adapter.dispatch: dbt calls duckdb__<name> when the target is
    DuckDB and bigquery__<name> when it's BigQuery. The models just call
    the plain name and work on both.
#}


{# The app stored dates as text, sometimes 2026-03-05, sometimes 05/03/2026 #}
{% macro parse_flexible_date(column) -%}
    {{ return(adapter.dispatch('parse_flexible_date')(column)) }}
{%- endmacro %}

{% macro duckdb__parse_flexible_date(column) -%}
    cast(coalesce(
        try_strptime(trim({{ column }}), '%Y-%m-%d'),
        try_strptime(trim({{ column }}), '%d/%m/%Y')
    ) as date)
{%- endmacro %}

{% macro bigquery__parse_flexible_date(column) -%}
    coalesce(
        safe.parse_date('%Y-%m-%d', trim({{ column }})),
        safe.parse_date('%d/%m/%Y', trim({{ column }}))
    )
{%- endmacro %}


{# "£12.50" -> 12.50, or null if it isn't a number #}
{% macro parse_money(column) -%}
    {{ return(adapter.dispatch('parse_money')(column)) }}
{%- endmacro %}

{% macro duckdb__parse_money(column) -%}
    try_cast(replace(trim({{ column }}), '£', '') as decimal(12, 2))
{%- endmacro %}

{% macro bigquery__parse_money(column) -%}
    safe_cast(replace(trim({{ column }}), '£', '') as numeric)
{%- endmacro %}


{# Text to whole number, or null if it isn't one (empty strings included) #}
{% macro to_integer_or_null(column) -%}
    {{ return(adapter.dispatch('to_integer_or_null')(column)) }}
{%- endmacro %}

{% macro duckdb__to_integer_or_null(column) -%}
    try_cast(nullif(trim({{ column }}), '') as integer)
{%- endmacro %}

{% macro bigquery__to_integer_or_null(column) -%}
    safe_cast(nullif(trim({{ column }}), '') as int64)
{%- endmacro %}


{# Trim the ends and squash repeated spaces in the middle #}
{% macro clean_text(column) -%}
    {{ return(adapter.dispatch('clean_text')(column)) }}
{%- endmacro %}

{% macro duckdb__clean_text(column) -%}
    regexp_replace(trim({{ column }}), '\s+', ' ', 'g')
{%- endmacro %}

{% macro bigquery__clean_text(column) -%}
    regexp_replace(trim({{ column }}), r'\s+', ' ')
{%- endmacro %}


{# First day of the date's month, as a date #}
{% macro month_start(column) -%}
    {{ return(adapter.dispatch('month_start')(column)) }}
{%- endmacro %}

{% macro duckdb__month_start(column) -%}
    cast(date_trunc('month', {{ column }}) as date)
{%- endmacro %}

{% macro bigquery__month_start(column) -%}
    date_trunc({{ column }}, month)
{%- endmacro %}
