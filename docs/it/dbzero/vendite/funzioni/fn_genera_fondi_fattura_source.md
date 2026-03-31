{% include-markdown "it/dbzero/vendite/manual/fn_genera_fondi_fattura_source.md" %}
# ⚙️ Funzione `fn_genera_fondi_fattura_source`

```sql
CREATE FUNCTION fn_genera_fondi_fattura_source(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id integer, p_tipo_fondo_fattura_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_genera_fondi_fattura_source(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id integer, p_tipo_fondo_fattura_id bigint)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_updated INTEGER := 0;
    v_inserted INTEGER := 0;
BEGIN
    -- Guard: tutti i parametri obbligatori e > 0
    IF p_billing_account_id IS NULL OR p_billing_account_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_genera_fondi_fattura_source', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_billing_account_id', 'valore', p_billing_account_id), NULL::uuid, 'p_billing_account_id obbligatorio e > 0');
    END IF;
    IF p_utility_id IS NULL OR p_utility_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_genera_fondi_fattura_source', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_utility_id', 'valore', p_utility_id), NULL::uuid, 'p_utility_id obbligatorio e > 0');
    END IF;
    IF p_tipo_doc_fiscale_id IS NULL OR p_tipo_doc_fiscale_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_genera_fondi_fattura_source', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_tipo_doc_fiscale_id', 'valore', p_tipo_doc_fiscale_id), NULL::uuid, 'p_tipo_doc_fiscale_id obbligatorio e > 0');
    END IF;
    IF p_emittente_soggetto_ruolo_id IS NULL OR p_emittente_soggetto_ruolo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_genera_fondi_fattura_source', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_emittente_soggetto_ruolo_id', 'valore', p_emittente_soggetto_ruolo_id), NULL::uuid, 'p_emittente_soggetto_ruolo_id obbligatorio e > 0');
    END IF;
    IF p_valuta_id IS NULL OR p_valuta_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_genera_fondi_fattura_source', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_valuta_id', 'valore', p_valuta_id), NULL::uuid, 'p_valuta_id obbligatorio e > 0');
    END IF;
    IF p_tipo_fondo_fattura_id IS NULL OR p_tipo_fondo_fattura_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_genera_fondi_fattura_source', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_tipo_fondo_fattura_id', 'valore', p_tipo_fondo_fattura_id), NULL::uuid, 'p_tipo_fondo_fattura_id obbligatorio e > 0');
    END IF;

    -- 1) Update source esistenti non assegnate
    WITH base AS (
        SELECT f.id AS fattura_sorgente_id,
               (COALESCE(sf.saldo, 0) - COALESCE(sc.saldo_contabile, 0))::NUMERIC AS importo_target
          FROM vendite.fatture f
          CROSS JOIN LATERAL pagamenti.fn_get_saldo_fattura(f.id) sf
          CROSS JOIN LATERAL pagamenti.fn_get_saldo_fattura_contabili(f.id) sc
         WHERE f.minimo IS TRUE
           AND f.billing_account_id = p_billing_account_id
           AND f.tipo_doc_fiscale_id = p_tipo_doc_fiscale_id
           AND f.emittente_soggetto_ruolo_id = p_emittente_soggetto_ruolo_id
           AND f.valuta_id = p_valuta_id
    ), upd AS (
        UPDATE vendite.fatture_fondi_fattura_source s
           SET importo = b.importo_target,
               stato = CASE WHEN COALESCE(b.importo_target, 0) = 0 THEN 'ANNULLATO' ELSE 'DISPONIBILE' END,
               utility_id = p_utility_id,
               data_update = now(), user_update = current_user
          FROM base b
         WHERE s.fattura_sorgente_id = b.fattura_sorgente_id
           AND s.tipo_fondo_fattura_id = p_tipo_fondo_fattura_id
           AND s.fattura_figlia_id IS NULL
           AND (s.importo IS DISTINCT FROM b.importo_target
                OR s.stato IS DISTINCT FROM (CASE WHEN COALESCE(b.importo_target, 0) = 0 THEN 'ANNULLATO' ELSE 'DISPONIBILE' END)
                OR s.utility_id IS DISTINCT FROM p_utility_id)
        RETURNING s.id
    )
    SELECT COUNT(*)::INTEGER INTO v_updated FROM upd;

    -- 2) Insert nuove source DISPONIBILE
    WITH base AS (
        SELECT f.id AS fattura_sorgente_id,
               (COALESCE(sf.saldo, 0) - COALESCE(sc.saldo_contabile, 0))::NUMERIC AS importo_target
          FROM vendite.fatture f
          CROSS JOIN LATERAL pagamenti.fn_get_saldo_fattura(f.id) sf
          CROSS JOIN LATERAL pagamenti.fn_get_saldo_fattura_contabili(f.id) sc
         WHERE f.minimo IS TRUE
           AND f.billing_account_id = p_billing_account_id
           AND f.tipo_doc_fiscale_id = p_tipo_doc_fiscale_id
           AND f.emittente_soggetto_ruolo_id = p_emittente_soggetto_ruolo_id
           AND f.valuta_id = p_valuta_id
           AND (COALESCE(sf.saldo, 0) - COALESCE(sc.saldo_contabile, 0)) <> 0
    ), ins AS (
        INSERT INTO vendite.fatture_fondi_fattura_source (
            fattura_sorgente_id, tipo_fondo_fattura_id, importo, stato,
            fattura_figlia_id, data_assegnazione, user_assegnazione,
            billing_account_id, utility_id, tipo_doc_fiscale_id,
            emittente_soggetto_ruolo_id, valuta_id, meta, attivo,
            data_insert, user_insert, data_update, user_update
        )
        SELECT b.fattura_sorgente_id, p_tipo_fondo_fattura_id, b.importo_target,
               'DISPONIBILE', NULL, NULL, NULL,
               p_billing_account_id, p_utility_id, p_tipo_doc_fiscale_id,
               p_emittente_soggetto_ruolo_id, p_valuta_id, '{}'::jsonb, TRUE,
               now(), current_user, now(), current_user
          FROM base b
         WHERE NOT EXISTS (
             SELECT 1 FROM vendite.fatture_fondi_fattura_source s
              WHERE s.fattura_sorgente_id = b.fattura_sorgente_id
                AND s.tipo_fondo_fattura_id = p_tipo_fondo_fattura_id
         )
        RETURNING id
    )
    SELECT COUNT(*)::INTEGER INTO v_inserted FROM ins;

    RETURN COALESCE(v_updated, 0) + COALESCE(v_inserted, 0);
END;
$function$

COMMENT ON FUNCTION vendite.fn_genera_fondi_fattura_source(p_billing_account_id bigint, p_utility_id integer, p_tipo_doc_fiscale_id bigint, p_emittente_soggetto_ruolo_id bigint, p_valuta_id integer, p_tipo_fondo_fattura_id bigint)
IS 'Sincronizza source fondi fattura sul saldo effettivo (saldo fattura - saldo contabile postabile).';
```

---
{% include-markdown "signature-core.md" %}
