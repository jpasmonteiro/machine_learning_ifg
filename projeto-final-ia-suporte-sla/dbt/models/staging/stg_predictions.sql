-- Staging das predicoes do modelo (conjunto de teste, fora da amostra).
select
    ticket_id,
    cast(y_true as integer)        as sla_breach_real,
    -- 'double precision' e' o tipo padrao ANSI: funciona em DuckDB, Postgres e
    -- Snowflake. O atalho 'double' so' existe no DuckDB e quebra a portabilidade.
    cast(proba_breach as double precision) as proba_breach,
    cast(y_pred as integer)        as sla_breach_previsto,
    modelo
from {{ source('raw', 'predictions') }}
