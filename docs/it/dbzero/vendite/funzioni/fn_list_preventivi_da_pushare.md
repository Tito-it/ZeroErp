{% include-markdown "it/dbzero/vendite/manual/fn_list_preventivi_da_pushare.md" %}
# ⚙️ Funzione `fn_list_preventivi_da_pushare`

```sql
CREATE FUNCTION fn_list_preventivi_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_list_preventivi_da_pushare(p_competenza_mese date DEFAULT NULL::date, p_billing_account_id bigint DEFAULT NULL::bigint, p_limit integer DEFAULT NULL::integer)
 RETURNS TABLE(preventivo_id bigint, preventivo_uid uuid, riga_id bigint, billing_account_id bigint, utility_id integer, emittente_soggetto_ruolo_id bigint, competenza_dal date, competenza_al date, fatturazione_immediata boolean, sorgente_tipo_id bigint, sorgente_uid text, segment_key character varying, articolo_id uuid, istanza_utility_id bigint, data_attivita date, uom_id bigint, quantita numeric, qta_operativa numeric, uom_operativa_id bigint, factor_to_base numeric, competenza_mese date, prezzo_snapshot numeric, prezzo_bloccato boolean, pricing_mode character varying, tipo_movimento character varying, tipo_consumo character varying, valuta_id integer, meta jsonb, tipo_doc_fiscale_id bigint)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_sorgente_tipo_id    config.sorgenti.id%TYPE;
    v_tipo_doc_fiscale_id config.sorgenti.tipo_doc_fiscale_id%TYPE;
    v_stato_accettato_id  config.stati_doc_preventivi.id%TYPE;
BEGIN
    SELECT s.id, s.tipo_doc_fiscale_id INTO v_sorgente_tipo_id, v_tipo_doc_fiscale_id
      FROM config.sorgenti s WHERE s.codice = 'PREVENTIVO' AND s.attivo IS TRUE LIMIT 1;

    IF v_sorgente_tipo_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_list_preventivi_da_pushare', 'E_CODICE',
            jsonb_build_object('codice', 'PREVENTIVO'), NULL::uuid, 'PREVENTIVO', 'config.sorgenti');
    END IF;

    SELECT s.id INTO v_stato_accettato_id
      FROM config.stati_doc_preventivi s WHERE s.codice = 'ACCETTATO' AND s.attivo IS TRUE LIMIT 1;

    RETURN QUERY
    SELECT p.id, p.uid, pr.id, p.billing_account_id, p.utility_id,
           anagrafiche.fn_get_emittente_fiscale_id(p.billing_account_id),
           p.validita_dal, p.validita_al, p.fatturazione_immediata,
           v_sorgente_tipo_id, p.uid::text,
           ('PREV:' || p.uid::text || ':R:' || pr.id::text)::VARCHAR,
           pr.articolo_id, p.istanza_utility_id,
           COALESCE(p.validita_dal, p.data), NULL::BIGINT,
           pr.quantita, pr.qta_operativa, pr.uom_operativa_id,
           COALESCE(pr.factor_to_base, 1::NUMERIC),
           date_trunc('month', COALESCE(p.validita_dal, p.data))::DATE,
           pr.prezzo_unitario, COALESCE(p.fatturazione_immediata, FALSE),
           'FIXED'::VARCHAR, 'NORMALE'::VARCHAR, 'CONGUAGLIO'::VARCHAR,
           p.valuta_id,
           jsonb_build_object('preventivo_numero', p.numero, 'preventivo_rev', p.rev,
               'tipo_commessa', 'REALE', 'policy_fatturazione', 'DA_DOCUMENTO'),
           v_tipo_doc_fiscale_id
      FROM vendite.preventivi p
      JOIN vendite.preventivi_righe pr ON pr.preventivo_id = p.id AND pr.attivo IS TRUE AND pr.quantita > 0 AND pr.prezzo_unitario >= 0
     WHERE p.billing_account_id IS NOT NULL AND p.utility_id IS NOT NULL
       AND (v_stato_accettato_id IS NULL OR p.stato_doc_preventivo_id = v_stato_accettato_id)
       AND (p_competenza_mese IS NULL OR date_trunc('month', COALESCE(p.validita_dal, p.data))::DATE = p_competenza_mese)
       AND (p_billing_account_id IS NULL OR p.billing_account_id = p_billing_account_id)
       AND NOT EXISTS (
           SELECT 1 FROM vendite.commesse_attivita ca
            WHERE ca.segment_key = 'PREV:' || p.uid::text || ':R:' || pr.id::text
              AND ca.stato_emissione = 'EMESSA'
       )
     ORDER BY p.id, pr.id LIMIT p_limit;
END;
$function$

COMMENT ON FUNCTION vendite.fn_list_preventivi_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer)
IS 'Righe preventivo eligible al push su commessa (stato ACCETTATO).';
```

---
{% include-markdown "signature-core.md" %}
