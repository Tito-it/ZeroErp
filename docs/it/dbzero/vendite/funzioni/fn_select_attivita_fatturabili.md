{% include-markdown "it/dbzero/vendite/manual/fn_select_attivita_fatturabili.md" %}
# ⚙️ Funzione `fn_select_attivita_fatturabili`

```sql
CREATE FUNCTION fn_select_attivita_fatturabili(p_competenza_mese date, p_tipo_doc_fiscale_id bigint, p_lock_batch_id uuid, p_lock boolean, p_data_fatturazione date, p_billing_account_id bigint, p_utility_id integer, p_valuta_id integer, p_emittente_soggetto_ruolo_id bigint, p_area_geografica_id bigint, p_limit integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_select_attivita_fatturabili(p_competenza_mese date, p_tipo_doc_fiscale_id bigint, p_lock_batch_id uuid DEFAULT NULL::uuid, p_lock boolean DEFAULT false, p_data_fatturazione date DEFAULT CURRENT_DATE, p_billing_account_id bigint DEFAULT NULL::bigint, p_utility_id integer DEFAULT NULL::integer, p_valuta_id integer DEFAULT NULL::integer, p_emittente_soggetto_ruolo_id bigint DEFAULT NULL::bigint, p_area_geografica_id bigint DEFAULT NULL::bigint, p_limit integer DEFAULT NULL::integer)
 RETURNS SETOF vendite.attivita_fatturabili
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_competenza DATE;
    v_data_fatturazione DATE;
    v_where TEXT;
    v_limit TEXT;
    v_sql TEXT;
BEGIN
    IF p_competenza_mese IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_select_attivita_fatturabili', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_competenza_mese', 'valore', NULL), NULL::uuid, 'p_competenza_mese obbligatoria');
    END IF;
    IF p_tipo_doc_fiscale_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_select_attivita_fatturabili', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_tipo_doc_fiscale_id', 'valore', NULL), NULL::uuid, 'p_tipo_doc_fiscale_id obbligatorio');
    END IF;
    IF p_lock AND p_lock_batch_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_select_attivita_fatturabili', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lock_batch_id', 'valore', NULL), NULL::uuid, 'p_lock_batch_id obbligatorio quando p_lock=true');
    END IF;

    v_competenza := date_trunc('month', p_competenza_mese)::DATE;
    v_data_fatturazione := COALESCE(p_data_fatturazione, CURRENT_DATE);

    v_where := ' WHERE a.approvato IS TRUE AND a.fatturato IS FALSE AND a.sospesa IS FALSE AND COALESCE(a.lock_in_fatturazione, false) IS FALSE'
        || ' AND (a.posticipa_al IS NULL OR a.posticipa_al <= ' || quote_literal(v_data_fatturazione) || ')'
        || ' AND a.competenza_mese <= ' || quote_literal(v_competenza)
        || ' AND a.tipo_doc_fiscale_id = ' || quote_literal(p_tipo_doc_fiscale_id);

    IF p_billing_account_id IS NOT NULL THEN v_where := v_where || ' AND a.billing_account_id = ' || quote_literal(p_billing_account_id); END IF;
    IF p_utility_id IS NOT NULL THEN v_where := v_where || ' AND ba.utility_id = ' || quote_literal(p_utility_id); END IF;
    IF p_valuta_id IS NOT NULL THEN v_where := v_where || ' AND a.valuta_id = ' || quote_literal(p_valuta_id); END IF;
    IF p_emittente_soggetto_ruolo_id IS NOT NULL THEN
        v_where := v_where || ' AND a.billing_account_id IS NOT NULL AND anagrafiche.fn_get_emittente_fiscale_id(a.billing_account_id) = ' || quote_literal(p_emittente_soggetto_ruolo_id);
    END IF;
    IF p_area_geografica_id IS NOT NULL THEN v_where := v_where || ' AND a.area_geografica_id = ' || quote_literal(p_area_geografica_id); END IF;

    v_limit := CASE WHEN p_limit IS NOT NULL THEN ' LIMIT ' || p_limit::TEXT ELSE '' END;

    IF p_lock THEN
        v_sql := 'WITH candidati AS (SELECT a.id FROM vendite.attivita_fatturabili a JOIN anagrafiche.billing_account ba ON ba.id = a.billing_account_id' || v_where || ' ORDER BY a.data_attivita, a.id' || v_limit || ' FOR UPDATE OF a SKIP LOCKED) UPDATE vendite.attivita_fatturabili a SET lock_in_fatturazione = true, lock_batch_id = ' || quote_literal(p_lock_batch_id) || ', stato_esecuzione = ''PENDING'', data_update = now(), user_update = current_user FROM candidati c WHERE a.id = c.id AND a.fatturato IS FALSE AND COALESCE(a.lock_in_fatturazione, false) IS FALSE RETURNING a.*';
    ELSE
        v_sql := 'WITH candidati AS (SELECT a.id FROM vendite.attivita_fatturabili a JOIN anagrafiche.billing_account ba ON ba.id = a.billing_account_id' || v_where || ' ORDER BY a.data_attivita, a.id' || v_limit || ') SELECT a.* FROM vendite.attivita_fatturabili a JOIN candidati c ON c.id = a.id ORDER BY a.data_attivita, a.id';
    END IF;

    RETURN QUERY EXECUTE v_sql;
END;
$function$

COMMENT ON FUNCTION vendite.fn_select_attivita_fatturabili(p_competenza_mese date, p_tipo_doc_fiscale_id bigint, p_lock_batch_id uuid, p_lock boolean, p_data_fatturazione date, p_billing_account_id bigint, p_utility_id integer, p_valuta_id integer, p_emittente_soggetto_ruolo_id bigint, p_area_geografica_id bigint, p_limit integer)
IS 'Select attivita_fatturabili eleggibili con lock opzionale e stato_esecuzione=PENDING.';
```

---
{% include-markdown "signature-core.md" %}
