-- Dimensao de canal de atendimento.
select row_number() over (order by channel) as channel_key, channel
from (select distinct channel from {{ ref('stg_tickets') }})
