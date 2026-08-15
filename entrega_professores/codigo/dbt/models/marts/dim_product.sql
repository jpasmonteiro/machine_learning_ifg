-- Dimensao de produto.
select row_number() over (order by product) as product_key, product
from (select distinct product from {{ ref('stg_tickets') }})
