{% include-markdown "it/dbzero/vendite/manual/fn_get_arrotondamento_scope.md" %}
# ⚙️ Funzione `fn_get_arrotondamento_scope`

```sql
CREATE FUNCTION fn_get_arrotondamento_scope(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_arrotondamento_scope(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id integer)
 RETURNS numeric
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_saldo vendite.fatture_arrotondamenti_scope.saldo_arrotondamento%TYPE;
BEGIN
    -- Guard: tutti i parametri obbligatori e > 0
    IF p_billing_account_id IS NULL OR p_billing_account_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_get_arrotondamento_scope', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_billing_account_id', 'valore', p_billing_account_id), NULL::uuid, 'p_billing_account_id obbligatorio e > 0');
    END IF;
    IF p_utility_id IS NULL OR p_utility_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_get_arrotondamento_scope', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_utility_id', 'valore', p_utility_id), NULL::uuid, 'p_utility_id obbligatorio e > 0');
    END IF;
    IF p_tipo_doc_fiscale_id IS NULL OR p_tipo_doc_fiscale_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_get_arrotondamento_scope', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_tipo_doc_fiscale_id', 'valore', p_tipo_doc_fiscale_id), NULL::uuid, 'p_tipo_doc_fiscale_id obbligatorio e > 0');
    END IF;
    IF p_emittente_soggetto_ruolo_id IS NULL OR p_emittente_soggetto_ruolo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_get_arrotondamento_scope', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_emittente_soggetto_ruolo_id', 'valore', p_emittente_soggetto_ruolo_id), NULL::uuid, 'p_emittente_soggetto_ruolo_id obbligatorio e > 0');
    END IF;
    IF p_valuta_id IS NULL OR p_valuta_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_get_arrotondamento_scope', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_valuta_id', 'valore', p_valuta_id), NULL::uuid, 'p_valuta_id obbligatorio e > 0');
    END IF;

    SELECT s.saldo_arrotondamento INTO v_saldo
      FROM vendite.fatture_arrotondamenti_scope s
     WHERE s.billing_account_id = p_billing_account_id
       AND s.utility_id = p_utility_id
       AND s.tipo_doc_fiscale_id = p_tipo_doc_fiscale_id
       AND s.emittente_soggetto_ruolo_id = p_emittente_soggetto_ruolo_id
       AND s.valuta_id = p_valuta_id;

    RETURN COALESCE(v_saldo, 0);
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
