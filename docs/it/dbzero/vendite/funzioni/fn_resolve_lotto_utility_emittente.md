{% include-markdown "it/dbzero/vendite/manual/fn_resolve_lotto_utility_emittente.md" %}
# ⚙️ Funzione `fn_resolve_lotto_utility_emittente`

```sql
CREATE FUNCTION fn_resolve_lotto_utility_emittente(p_billing_account_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint, p_scope text, p_caller text, p_check_emittente_attivo boolean)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_resolve_lotto_utility_emittente(p_billing_account_id bigint DEFAULT NULL::bigint, p_utility_id integer DEFAULT NULL::integer, p_emittente_soggetto_ruolo_id bigint DEFAULT NULL::bigint, p_scope text DEFAULT 'LOTTO'::text, p_caller text DEFAULT 'fn_resolve_lotto_utility_emittente'::text, p_check_emittente_attivo boolean DEFAULT true)
 RETURNS TABLE(resolved_utility_id integer, resolved_emittente_soggetto_ruolo_id bigint)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_utility_from_ba  anagrafiche.billing_account.utility_id%TYPE;
    v_emittente_from_ba anagrafiche.soggetti_ruoli.id%TYPE;
    v_emittente_attivo BOOLEAN;
BEGIN
    -- Guard: parametri opzionali ma se forniti devono essere > 0
    IF p_billing_account_id IS NOT NULL AND p_billing_account_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', p_caller, 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_billing_account_id', 'valore', p_billing_account_id), NULL::uuid, 'p_billing_account_id se fornito deve essere > 0');
    END IF;

    IF p_utility_id IS NOT NULL AND p_utility_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', p_caller, 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_utility_id', 'valore', p_utility_id), NULL::uuid, 'p_utility_id se fornito deve essere > 0');
    END IF;

    IF p_emittente_soggetto_ruolo_id IS NOT NULL AND p_emittente_soggetto_ruolo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', p_caller, 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_emittente_soggetto_ruolo_id', 'valore', p_emittente_soggetto_ruolo_id), NULL::uuid, 'p_emittente_soggetto_ruolo_id se fornito deve essere > 0');
    END IF;

    -- Risolvi utility da BA
    resolved_utility_id := p_utility_id;

    IF p_billing_account_id IS NOT NULL THEN
        SELECT ba.utility_id INTO v_utility_from_ba
          FROM anagrafiche.billing_account ba WHERE ba.id = p_billing_account_id;

        IF v_utility_from_ba IS NULL THEN
            PERFORM script.fn_log_and_raise_error('vendite', p_caller, 'E_VALORE_MANCANTE',
                jsonb_build_object('billing_account_id', p_billing_account_id), NULL::uuid, concat('utility non risolta da BA ', p_billing_account_id));
        END IF;

        IF resolved_utility_id IS NOT NULL AND resolved_utility_id <> v_utility_from_ba THEN
            PERFORM script.fn_log_and_raise_error('vendite', p_caller, 'E_CLIENTE_UTILITY_MISMATCH_BA',
                jsonb_build_object('billing_account_id', p_billing_account_id, 'utility_parametro', resolved_utility_id, 'utility_ba', v_utility_from_ba),
                NULL::uuid, p_billing_account_id::text, resolved_utility_id::text, v_utility_from_ba::text);
        END IF;

        resolved_utility_id := COALESCE(resolved_utility_id, v_utility_from_ba);
    END IF;

    -- Risolvi emittente da BA (include fallback default globale)
    v_emittente_from_ba := anagrafiche.fn_get_emittente_fiscale_id(p_billing_account_id);

    IF p_emittente_soggetto_ruolo_id IS NOT NULL
       AND p_billing_account_id IS NOT NULL
       AND p_emittente_soggetto_ruolo_id <> v_emittente_from_ba THEN
        PERFORM script.fn_log_and_raise_error('vendite', p_caller, 'E_LOTTO_PARAMETRO_NON_COERENTE',
            jsonb_build_object('parametro', 'emittente_soggetto_ruolo_id', 'atteso', v_emittente_from_ba, 'ricevuto', p_emittente_soggetto_ruolo_id),
            NULL::uuid, 'emittente_soggetto_ruolo_id', 'BA');
    END IF;

    resolved_emittente_soggetto_ruolo_id := COALESCE(p_emittente_soggetto_ruolo_id, v_emittente_from_ba);

    -- Verifica emittente attivo
    IF p_check_emittente_attivo THEN
        SELECT EXISTS (
            SELECT 1 FROM anagrafiche.emittenti_fiscali ef
             WHERE ef.soggetto_ruolo_id = resolved_emittente_soggetto_ruolo_id AND ef.attivo IS TRUE
        ) INTO v_emittente_attivo;

        IF COALESCE(v_emittente_attivo, FALSE) IS FALSE THEN
            PERFORM script.fn_log_and_raise_error('vendite', p_caller, 'E_CODICE',
                jsonb_build_object('emittente_soggetto_ruolo_id', resolved_emittente_soggetto_ruolo_id),
                NULL::uuid, resolved_emittente_soggetto_ruolo_id::text, 'anagrafiche.emittenti_fiscali');
        END IF;
    END IF;

    RETURN NEXT;
END;
$function$

COMMENT ON FUNCTION vendite.fn_resolve_lotto_utility_emittente(p_billing_account_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint, p_scope text, p_caller text, p_check_emittente_attivo boolean)
IS 'Helper condiviso: risolve e valida utility/emittente per lotti con fallback default emittente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
