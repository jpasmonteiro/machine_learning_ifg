-- Dimensao de categoria do chamado.
select row_number() over (order by category) as category_key, category
from (select distinct category from {{ ref('stg_tickets') }})
