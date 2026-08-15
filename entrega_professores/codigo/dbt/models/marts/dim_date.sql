-- Dimensao de data (grao diario).
select
    created_date                              as date_key,
    extract('year'  from created_date)        as ano,
    extract('month' from created_date)        as mes,
    extract('day'   from created_date)        as dia,
    extract('dow'   from created_date)        as dia_semana
from (select distinct created_date from {{ ref('stg_tickets') }})
