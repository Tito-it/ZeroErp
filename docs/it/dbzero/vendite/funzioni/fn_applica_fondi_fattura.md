{% include-markdown "it/dbzero/vendite/manual/fn_applica_fondi_fattura.md" %}
# ⚙️ Funzione `fn_applica_fondi_fattura`

```sql
CREATE FUNCTION fn_applica_fondi_fattura(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id integer, p_fattura_figlia_id bigint, p_tipo_fondo_fattura_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_applica_fondi_fattura(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id integer, p_fattura_figlia_id bigint, p_tipo_fondo_fattura_id bigint DEFAULT NULL::bigint)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_inserted INTEGER := 0;
BEGIN
    -- Guard: parametri obbligatori
    IF p_billing_account_id IS NULL OR p_billing_account_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_applica_fondi_fattura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_billing_account_id', 'valore', p_billing_account_id),
            NULL::uuid, 'p_billing_account_id obbligatorio e > 0'
        );
    END IF;

    IF p_utility_id IS NULL OR p_utility_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_applica_fondi_fattura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_utility_id', 'valore', p_utility_id),
            NULL::uuid, 'p_utility_id obbligatorio e > 0'
        );
    END IF;

    IF p_tipo_doc_fiscale_id IS NULL OR p_tipo_doc_fiscale_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_applica_fondi_fattura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_tipo_doc_fiscale_id', 'valore', p_tipo_doc_fiscale_id),
            NULL::uuid, 'p_tipo_doc_fiscale_id obbligatorio e > 0'
        );
    END IF;

    IF p_emittente_soggetto_ruolo_id IS NULL OR p_emittente_soggetto_ruolo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_applica_fondi_fattura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_emittente_soggetto_ruolo_id', 'valore', p_emittente_soggetto_ruolo_id),
            NULL::uuid, 'p_emittente_soggetto_ruolo_id obbligatorio e > 0'
        );
    END IF;

    IF p_valuta_id IS NULL OR p_valuta_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_applica_fondi_fattura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_valuta_id', 'valore', p_valuta_id),
            NULL::uuid, 'p_valuta_id obbligatorio e > 0'
        );
    END IF;

    IF p_fattura_figlia_id IS NULL OR p_fattura_figlia_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_applica_fondi_fattura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_fattura_figlia_id', 'valore', p_fattura_figlia_id),
            NULL::uuid, 'p_fattura_figlia_id obbligatorio e > 0'
        );
    END IF;

    IF p_tipo_fondo_fattura_id IS NOT NULL AND p_tipo_fondo_fattura_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_applica_fondi_fattura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_tipo_fondo_fattura_id', 'valore', p_tipo_fondo_fattura_id),
            NULL::uuid, 'p_tipo_fondo_fattura_id se fornito deve essere > 0'
        );
    END IF;

    -- Applica fondi: CTE con lock, update source, insert righe
    WITH src AS (
        SELECT s.*
          FROM vendite.fatture_fondi_fattura_source s
         WHERE s.stato = 'DISPONIBILE'
           AND s.fattura_figlia_id IS NULL
           AND s.billing_account_id = p_billing_account_id
           AND s.utility_id = p_utility_id
           AND s.tipo_doc_fiscale_id = p_tipo_doc_fiscale_id
           AND s.emittente_soggetto_ruolo_id = p_emittente_soggetto_ruolo_id
           AND s.valuta_id = p_valuta_id
           AND (p_tipo_fondo_fattura_id IS NULL OR s.tipo_fondo_fattura_id = p_tipo_fondo_fattura_id)
           FOR UPDATE SKIP LOCKED
    ), upd AS (
        UPDATE vendite.fatture_fondi_fattura_source s
           SET fattura_figlia_id = p_fattura_figlia_id,
               data_assegnazione = now(),
               user_assegnazione = current_user,
               stato = 'ASSEGNATO',
               data_update = now(),
               user_update = current_user
          FROM src
         WHERE s.id = src.id
        RETURNING s.*
    )
    INSERT INTO vendite.fatture_fondi_fattura (
        fattura_id, tipo_fondo_fattura_id, importo,
        riferimento_fattura_id, meta, attivo,
        data_insert, user_insert, data_update, user_update
    )
    SELECT
        p_fattura_figlia_id, u.tipo_fondo_fattura_id, u.importo,
        u.fattura_sorgente_id, u.meta, TRUE,
        now(), current_user, now(), current_user
      FROM upd u;

    GET DIAGNOSTICS v_inserted = ROW_COUNT;

    RETURN v_inserted;
END;
$function$

COMMENT ON FUNCTION vendite.fn_applica_fondi_fattura(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id integer, p_fattura_figlia_id bigint, p_tipo_fondo_fattura_id bigint)
IS 'Applica fondi DISPONIBILE alla fattura figlia, crea righe fondi e marca source come ASSEGNATO.';
```

---
{% include-markdown "signature-core.md" %}
