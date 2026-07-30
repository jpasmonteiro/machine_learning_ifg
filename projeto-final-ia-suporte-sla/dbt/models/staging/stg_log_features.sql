-- Staging das agregacoes dos logs de eventos (JSON semiestruturado).
select ticket_id, n_events, n_status_changes, reopened_from_log
from {{ source('raw', 'log_features') }}
