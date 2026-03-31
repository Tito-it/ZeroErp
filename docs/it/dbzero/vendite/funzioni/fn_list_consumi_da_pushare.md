{% include-markdown "it/dbzero/vendite/manual/fn_list_consumi_da_pushare.md" %}
# ⚙️ Funzione `fn_list_consumi_da_pushare`

```sql
CREATE FUNCTION fn_list_consumi_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_list_consumi_da_pushare(p_competenza_mese date DEFAULT NULL::date, p_billing_account_id bigint DEFAULT NULL::bigint, p_limit integer DEFAULT NULL::integer)
 RETURNS TABLE(consumo_id bigint, consumo_uid uuid, billing_account_id bigint, utility_id integer, emittente_soggetto_ruolo_id bigint, competenza_dal date, competenza_al date, fatturazione_immediata boolean, sorgente_tipo_id bigint, sorgente_uid text, segment_key character varying, articolo_id uuid, istanza_utility_id bigint, data_attivita date, uom_id bigint, quantita numeric, qta_operativa numeric, uom_operativa_id bigint, factor_to_base numeric, competenza_mese date, prezzo_snapshot numeric, prezzo_bloccato boolean, pricing_mode character varying, tipo_movimento character varying, tipo_consumo character varying, valuta_id integer, meta jsonb, tipo_doc_fiscale_id bigint)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_sorgente_tipo_id    config.sorgenti.id%TYPE;
    v_tipo_doc_fiscale_id config.sorgenti.tipo_doc_fiscale_id%TYPE;
BEGIN
    SELECT s.id, s.tipo_doc_fiscale_id INTO v_sorgente_tipo_id, v_tipo_doc_fiscale_id
      FROM config.sorgenti s WHERE s.codice = 'ATTIVITA_CONSUMI' AND s.attivo IS TRUE LIMIT 1;

    IF v_sorgente_tipo_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_list_consumi_da_pushare', 'E_CODICE',
            jsonb_build_object('codice', 'ATTIVITA_CONSUMI'), NULL::uuid, 'ATTIVITA_CONSUMI', 'config.sorgenti');
    END IF;

    RETURN QUERY
    SELECT ac.id, ac.uid, ac.billing_account_id, ba.utility_id,
           anagrafiche.fn_get_emittente_fiscale_id(ac.billing_account_id),
           ac.periodo_dal, ac.periodo_al, FALSE, v_sorgente_tipo_id,
           ac.uid::text, ('CONS:' || ac.uid::text)::VARCHAR, NULL::UUID,
           ba.istanza_utility_id, COALESCE(ac.periodo_dal, ac.competenza_mese),
           ac.uom_id, ac.consumo_totale, ac.consumo_totale, ac.uom_id,
           1::NUMERIC, ac.competenza_mese, NULL::NUMERIC, FALSE,
           'FIXED'::VARCHAR, 'NORMALE'::VARCHAR, 'CONSUMO'::VARCHAR,
           NULL::INTEGER,
           jsonb_build_object('consumo_uid', ac.uid, 'stato_calcolo', ac.stato_calcolo,
               'periodo_dal', ac.periodo_dal, 'periodo_al', ac.periodo_al,
               'tipo_commessa', 'AUTO', 'policy_fatturazione', 'DA_DOCUMENTO'),
           v_tipo_doc_fiscale_id
      FROM vendite.attivita_consumi ac
      JOIN anagrafiche.billing_account ba ON ba.id = ac.billing_account_id
     WHERE ac.stato_calcolo = 'OK' AND ac.fattura_id IS NULL
       AND (p_competenza_mese IS NULL OR ac.competenza_mese = p_competenza_mese)
       AND (p_billing_account_id IS NULL OR ac.billing_account_id = p_billing_account_id)
       AND NOT EXISTS (
           SELECT 1 FROM vendite.commesse_attivita ca
            WHERE ca.segment_key LIKE 'CONS:' || ac.uid::text || ':%'
              AND ca.stato_emissione = 'EMESSA'
       )
     ORDER BY ac.competenza_mese, ac.id LIMIT p_limit;
END;
$function$

COMMENT ON FUNCTION vendite.fn_list_consumi_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer)
IS 'Consumi eligible al push su commessa AUTO (stato_calcolo OK, non fatturati).';
```

---
{% include-markdown "signature-core.md" %}
