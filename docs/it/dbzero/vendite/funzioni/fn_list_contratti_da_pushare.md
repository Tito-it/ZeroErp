{% include-markdown "it/dbzero/vendite/manual/fn_list_contratti_da_pushare.md" %}
# ⚙️ Funzione `fn_list_contratti_da_pushare`

```sql
CREATE FUNCTION fn_list_contratti_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_list_contratti_da_pushare(p_competenza_mese date DEFAULT NULL::date, p_billing_account_id bigint DEFAULT NULL::bigint, p_limit integer DEFAULT NULL::integer)
 RETURNS TABLE(contratto_id bigint, contratto_uid uuid, riga_id bigint, billing_account_id bigint, utility_id integer, emittente_soggetto_ruolo_id bigint, competenza_dal date, competenza_al date, fatturazione_immediata boolean, sorgente_tipo_id bigint, sorgente_uid text, segment_key character varying, articolo_id uuid, istanza_utility_id bigint, data_attivita date, uom_id bigint, quantita numeric, qta_operativa numeric, uom_operativa_id bigint, factor_to_base numeric, competenza_mese date, prezzo_snapshot numeric, prezzo_bloccato boolean, pricing_mode character varying, tipo_movimento character varying, tipo_consumo character varying, valuta_id integer, meta jsonb, tipo_doc_fiscale_id bigint)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_sorgente_tipo_id    config.sorgenti.id%TYPE;
    v_tipo_doc_fiscale_id config.sorgenti.tipo_doc_fiscale_id%TYPE;
    v_stato_attivo_id     config.stati_doc_contratti.id%TYPE;
BEGIN
    SELECT s.id, s.tipo_doc_fiscale_id INTO v_sorgente_tipo_id, v_tipo_doc_fiscale_id
      FROM config.sorgenti s WHERE s.codice = 'CONTRATTO' AND s.attivo IS TRUE LIMIT 1;

    IF v_sorgente_tipo_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_list_contratti_da_pushare', 'E_CODICE',
            jsonb_build_object('codice', 'CONTRATTO'), NULL::uuid, 'CONTRATTO', 'config.sorgenti');
    END IF;

    SELECT s.id INTO v_stato_attivo_id
      FROM config.stati_doc_contratti s WHERE s.codice = 'ATTIVO' AND s.attivo IS TRUE LIMIT 1;

    RETURN QUERY
    SELECT c.id, c.uid, cr.id, c.billing_account_id, c.utility_id,
           anagrafiche.fn_get_emittente_fiscale_id(c.billing_account_id),
           c.valido_dal, c.valido_al, FALSE, v_sorgente_tipo_id, c.uid::text,
           ('CONTR:' || c.uid::text || ':R:' || cr.id::text || ':M:' ||
            to_char(date_trunc('month', COALESCE(c.valido_dal, c.data))::DATE, 'YYYY-MM'))::VARCHAR,
           cr.articolo_id, c.istanza_utility_id,
           COALESCE(c.valido_dal, c.data), NULL::BIGINT, cr.quantita_fissa,
           cr.qta_operativa, cr.uom_operativa_id, COALESCE(cr.factor_to_base, 1::NUMERIC),
           date_trunc('month', COALESCE(c.valido_dal, c.data))::DATE,
           cr.prezzo_unitario, (cr.prezzo_unitario IS NOT NULL),
           'FIXED'::VARCHAR, 'NORMALE'::VARCHAR,
           COALESCE(cr.tipo_erogazione, 'CANONE')::VARCHAR, NULL::INTEGER,
           jsonb_build_object('contratto_numero', c.numero, 'periodicita', cr.periodicita,
               'generazione_canone', cr.generazione_canone, 'competenza_canone', cr.competenza_canone,
               'tipo_erogazione', cr.tipo_erogazione, 'tipo_commessa', 'AUTO', 'policy_fatturazione', 'DA_DOCUMENTO'),
           v_tipo_doc_fiscale_id
      FROM vendite.contratti c
      JOIN vendite.contratti_righe cr ON cr.contratto_id = c.id AND COALESCE(cr.attivo, TRUE) IS TRUE
     WHERE c.billing_account_id IS NOT NULL
       AND (v_stato_attivo_id IS NULL OR c.stato_doc_contratto_id = v_stato_attivo_id)
       AND (c.valido_al IS NULL OR c.valido_al >= COALESCE(p_competenza_mese, CURRENT_DATE))
       AND (p_competenza_mese IS NULL OR date_trunc('month', COALESCE(c.valido_dal, c.data))::DATE = p_competenza_mese)
       AND (p_billing_account_id IS NULL OR c.billing_account_id = p_billing_account_id)
       AND NOT EXISTS (
           SELECT 1 FROM vendite.commesse_attivita ca
            WHERE ca.segment_key = 'CONTR:' || c.uid::text || ':R:' || cr.id::text
                || ':M:' || to_char(date_trunc('month', COALESCE(c.valido_dal, c.data))::DATE, 'YYYY-MM')
              AND ca.stato_emissione = 'EMESSA'
       )
     ORDER BY c.id, cr.id LIMIT p_limit;
END;
$function$

COMMENT ON FUNCTION vendite.fn_list_contratti_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer)
IS 'Righe contratto eligible al push su commessa (stato ATTIVO, in validita).';
```

---
{% include-markdown "signature-core.md" %}
