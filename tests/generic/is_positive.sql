{# Fails for any row where the column is zero or negative. #}
{% test is_positive(model, column_name) %}

select *
from {{ model }}
where {{ column_name }} <= 0

{% endtest %}
