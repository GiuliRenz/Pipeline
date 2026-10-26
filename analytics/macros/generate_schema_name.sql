{#
    Por defecto dbt concatena el schema del perfil con el personalizado (analytics_marts).
    Usamos el nombre personalizado tal cual para obtener schemas limpios: staging, intermediate, marts.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
