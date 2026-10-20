{% include-markdown "it/dbzero/vendite/manual/fn_set_arrotondamento_scope.md" %}
# ⚙️ Funzione `fn_set_arrotondamento_scope`

```sql
CREATE FUNCTION fn_set_arrotondamento_scope(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id integer, p_saldo numeric, p_termine_pagamento_id bigint, p_modalita_pagamento_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_set_arrotondamento_scope(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id integer, p_saldo numeric, p_termine_pagamento_id bigint DEFAULT NULL::bigint, p_modalita_pagamento_id integer DEFAULT NULL::integer)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
-- Scopo: scrive il saldo dell'ambito (upsert). Da D-N l'ambito
--        comprende anche le condizioni di pagamento.
-- Regole: l'upsert poggia su uq_fatture_arrotondamenti_scope_key, che
--         e' NULLS NOT DISTINCT: senza quella clausola due ambiti con
--         termine NULL non collidono e il saldo si sdoppia.
BEGIN
    INSERT INTO vendite.fatture_arrotondamenti_scope AS s (
        billing_account_id, utility_id, tipo_doc_fiscale_id,
        emittente_soggetto_ruolo_id, valuta_id,
        termine_pagamento_id, modalita_pagamento_id,
        saldo_arrotondamento
    )
    VALUES (
        p_billing_account_id, p_utility_id, p_tipo_doc_fiscale_id,
        p_emittente_soggetto_ruolo_id, p_valuta_id,
        p_termine_pagamento_id, p_modalita_pagamento_id,
        COALESCE(p_saldo, 0)
    )
    ON CONFLICT (billing_account_id, utility_id, tipo_doc_fiscale_id,
                 emittente_soggetto_ruolo_id, valuta_id,
                 termine_pagamento_id, modalita_pagamento_id)
    DO UPDATE SET saldo_arrotondamento = EXCLUDED.saldo_arrotondamento,
                  data_update = now(),
                  user_update = current_user;
END;
$function$

COMMENT ON FUNCTION vendite.fn_set_arrotondamento_scope(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id integer, p_saldo numeric, p_termine_pagamento_id bigint, p_modalita_pagamento_id integer)
IS 'Upsert del saldo arrotondamento dell''ambito. Da D-N l''ambito comprende (termine_pagamento_id, modalita_pagamento_id); l''ON CONFLICT poggia su uq_fatture_arrotondamenti_scope_key, che e'' NULLS NOT DISTINCT.';
```

</div>

---
{% include-markdown "signature-core.md" %}
