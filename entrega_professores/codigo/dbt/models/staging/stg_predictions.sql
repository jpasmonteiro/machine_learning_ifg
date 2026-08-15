-- Staging das predicoes do modelo (conjunto de teste, fora da amostra).
select
    ticket_id,
    cast(y_true as integer)        as sla_breach_real,
    cast(proba_breach as double)   as proba_breach,
    cast(y_pred as integer)        as sla_breach_previsto,
    modelo
from {{ source('raw', 'predictions') }}
