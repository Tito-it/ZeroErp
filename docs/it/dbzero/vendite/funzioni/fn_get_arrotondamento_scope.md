{% include-markdown "it/dbzero/vendite/manual/fn_get_arrotondamento_scope.md" %}
# ⚙️ Funzione `fn_get_arrotondamento_scope`

```sql
CREATE FUNCTION fn_get_arrotondamento_scope(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id integer, p_termine_pagamento_id bigint, p_modalita_pagamento_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_arrotondamento_scope(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id integer, p_termine_pagamento_id bigint DEFAULT NULL::bigint, p_modalita_pagamento_id integer DEFAULT NULL::integer)
 RETURNS numeric
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: saldo di arrotondamento accumulato nell'ambito. Da D-N
--        l'ambito comprende anche le condizioni di pagamento.
-- Regole: assenza di riga = saldo zero, non errore.
DECLARE
    v_saldo vendite.fatture_arrotondamenti_scope.saldo_arrotondamento%TYPE;
BEGIN
    SELECT s.saldo_arrotondamento
      INTO v_saldo
      FROM vendite.fatture_arrotondamenti_scope s
     WHERE s.billing_account_id = p_billing_account_id
       AND s.utility_id = p_utility_id
       AND s.tipo_doc_fiscale_id = p_tipo_doc_fiscale_id
       AND s.emittente_soggetto_ruolo_id = p_emittente_soggetto_ruolo_id
       AND s.valuta_id = p_valuta_id
       AND s.termine_pagamento_id  IS NOT DISTINCT FROM p_termine_pagamento_id
       AND s.modalita_pagamento_id IS NOT DISTINCT FROM p_modalita_pagamento_id;

    RETURN COALESCE(v_saldo, 0);
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_arrotondamento_scope(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id integer, p_termine_pagamento_id bigint, p_modalita_pagamento_id integer)
IS 'Saldo arrotondamento dell''ambito di compensazione. Da D-N l''ambito comprende (termine_pagamento_id, modalita_pagamento_id), confrontati con IS NOT DISTINCT FROM perche'' sono NULL nella maggioranza dei casi. Assenza di riga = 0.';
```

---
{% include-markdown "signature-core.md" %}
