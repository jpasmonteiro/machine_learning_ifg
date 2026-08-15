{#
  Usa o schema customizado (staging / analytics) diretamente, em vez de
  concatenar com o schema do target. Deixa os nomes limpos no warehouse.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
