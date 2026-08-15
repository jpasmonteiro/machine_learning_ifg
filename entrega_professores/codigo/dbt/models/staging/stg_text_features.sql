-- Staging dos atributos textuais (extraidos do texto livre do cliente).
select
    ticket_id, body_len, word_count, num_question, num_exclam,
    upper_ratio, urgency_hits, kw_refund, kw_cancel, kw_error
from {{ source('raw', 'text_features') }}
