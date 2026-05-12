{% include-markdown "it/dbzero/vendite/manual/fn_set_arrotondamento_scope.md" %}
# ⚙️ Funzione `fn_set_arrotondamento_scope`

```sql
CREATE FUNCTION fn_set_arrotondamento_scope(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id integer, p_saldo numeric)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_set_arrotondamento_scope(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id integer, p_saldo numeric)
 RETURNS numeric
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_saldo vendite.fatture_arrotondamenti_scope.saldo_arrotondamento%TYPE;
BEGIN
    IF p_billing_account_id IS NULL OR p_billing_account_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_set_arrotondamento_scope', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_billing_account_id', 'valore', p_billing_account_id), NULL::uuid, 'p_billing_account_id obbligatorio e > 0');
    END IF;
    IF p_utility_id IS NULL OR p_utility_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_set_arrotondamento_scope', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_utility_id', 'valore', p_utility_id), NULL::uuid, 'p_utility_id obbligatorio e > 0');
    END IF;
    IF p_tipo_doc_fiscale_id IS NULL OR p_tipo_doc_fiscale_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_set_arrotondamento_scope', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_tipo_doc_fiscale_id', 'valore', p_tipo_doc_fiscale_id), NULL::uuid, 'p_tipo_doc_fiscale_id obbligatorio e > 0');
    END IF;
    IF p_emittente_soggetto_ruolo_id IS NULL OR p_emittente_soggetto_ruolo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_set_arrotondamento_scope', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_emittente_soggetto_ruolo_id', 'valore', p_emittente_soggetto_ruolo_id), NULL::uuid, 'p_emittente_soggetto_ruolo_id obbligatorio e > 0');
    END IF;
    IF p_valuta_id IS NULL OR p_valuta_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_set_arrotondamento_scope', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_valuta_id', 'valore', p_valuta_id), NULL::uuid, 'p_valuta_id obbligatorio e > 0');
    END IF;
    IF p_saldo IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_set_arrotondamento_scope', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_saldo', 'valore', NULL), NULL::uuid, 'p_saldo obbligatorio');
    END IF;

    INSERT INTO vendite.fatture_arrotondamenti_scope (
        billing_account_id, utility_id, tipo_doc_fiscale_id, emittente_soggetto_ruolo_id,
        valuta_id, saldo_arrotondamento, data_insert, user_insert, data_update, user_update
    ) VALUES (
        p_billing_account_id, p_utility_id, p_tipo_doc_fiscale_id, p_emittente_soggetto_ruolo_id,
        p_valuta_id, p_saldo, now(), current_user, now(), current_user
    )
    ON CONFLICT (billing_account_id, utility_id, tipo_doc_fiscale_id, emittente_soggetto_ruolo_id, valuta_id)
    DO UPDATE SET saldo_arrotondamento = EXCLUDED.saldo_arrotondamento, data_update = now(), user_update = current_user
    RETURNING saldo_arrotondamento INTO v_saldo;

    RETURN v_saldo;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
