{# Fails if the same combination of columns appears more than once. #}
{% test unique_combination(model, columns) %}

select
    {{ columns | join(', ') }},
    count(*) as copies
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1

{% endtest %}
