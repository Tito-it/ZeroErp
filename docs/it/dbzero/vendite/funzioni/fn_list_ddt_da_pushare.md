{% include-markdown "it/dbzero/vendite/manual/fn_list_ddt_da_pushare.md" %}
# ⚙️ Funzione `fn_list_ddt_da_pushare`

```sql
CREATE FUNCTION fn_list_ddt_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer, p_ddt_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_list_ddt_da_pushare(p_competenza_mese date DEFAULT NULL::date, p_billing_account_id bigint DEFAULT NULL::bigint, p_limit integer DEFAULT NULL::integer, p_ddt_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(ddt_id bigint, ddt_uid uuid, riga_id bigint, billing_account_id bigint, utility_id integer, emittente_soggetto_ruolo_id bigint, competenza_dal date, competenza_al date, fatturazione_immediata boolean, sorgente_tipo_id bigint, sorgente_uid text, segment_key character varying, articolo_id uuid, istanza_utility_id bigint, data_attivita date, uom_id bigint, quantita numeric, qta_operativa numeric, uom_operativa_id bigint, factor_to_base numeric, competenza_mese date, prezzo_snapshot numeric, prezzo_bloccato boolean, pricing_mode character varying, tipo_movimento character varying, tipo_consumo character varying, valuta_id integer, meta jsonb, tipo_doc_fiscale_id bigint)
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_sorgente_tipo_id    config.sorgenti.id%TYPE;
  v_tipo_doc_fiscale_id config.sorgenti.tipo_doc_fiscale_id%TYPE;
BEGIN
  -- rev 2026-06-28 (analisi-hardcoded-codice §3a): sorgente e stato DDT
  -- risolti per codice_interno (immutabile), non per codice (mutabile).
  IF p_ddt_id IS NOT NULL AND p_ddt_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_list_ddt_da_pushare', 'E_PUSH_SORGENTE_ID_INVALIDO',
      jsonb_build_object('parametro', 'p_ddt_id', 'valore', p_ddt_id),
      NULL::uuid,
      'p_ddt_id', p_ddt_id::text
    );
  END IF;

  SELECT s.id, s.tipo_doc_fiscale_id
    INTO v_sorgente_tipo_id, v_tipo_doc_fiscale_id
  FROM config.sorgenti s
  WHERE s.codice_interno = 'DDT_VENDITA' AND s.attivo IS TRUE LIMIT 1;

  IF v_sorgente_tipo_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_list_ddt_da_pushare', 'E_CODICE',
      jsonb_build_object('codice', 'DDT_VENDITA'),
      NULL::uuid, 'DDT_VENDITA', 'config.sorgenti'
    );
  END IF;

  RETURN QUERY
  SELECT
    d.id, d.uid, dr.id,
    COALESCE(d.billing_account_id, src.src_billing_account_id),
    ba.utility_id,
    anagrafiche.fn_get_emittente_fiscale_id(COALESCE(d.billing_account_id, src.src_billing_account_id)),
    d.data, d.data,
    FALSE,
    v_sorgente_tipo_id,
    d.uid::text,
    ('DDT:' || d.uid::text || ':R:' || dr.id::text)::varchar,
    dr.articolo_id,
    ba.istanza_utility_id,
    d.data,
    -- uom_id canonica da catalogo.articoli (fix bug proiezione NULL)
    a.uom_id,
    dr.quantita,
    dr.qta_operativa,
    dr.uom_operativa_id,
    COALESCE(dr.factor_to_base, 1::numeric),
    date_trunc('month', d.data)::date,
    COALESCE(dr.prezzo_unitario, src.src_prezzo_unitario),
    (COALESCE(dr.prezzo_unitario, src.src_prezzo_unitario) IS NOT NULL),
    'FIXED'::varchar,
    'NORMALE'::varchar,
    'CONGUAGLIO'::varchar,
    COALESCE(d.valuta_id, src.src_valuta_id),
    jsonb_build_object(
      'ddt_numero',          d.numero,
      'ddt_anno',            d.anno,
      'ddt_serie',           d.serie,
      'ordine_sorgente_uid', src.src_ordine_uid,
      'ordine_fatturaz_trg', src.src_fatturazione_trigger,
      'tipo_commessa',       'AUTO',
      'policy_fatturazione', 'DA_DOCUMENTO'
    ),
    v_tipo_doc_fiscale_id
  FROM vendite.ddt d
  JOIN config.stati_doc_ddt sdd ON sdd.id = d.stato_doc_ddt_id
  JOIN vendite.ddt_righe dr
    ON dr.ddt_id = d.id
   AND dr.attivo IS TRUE
  JOIN catalogo.articoli a ON a.id = dr.articolo_id
  LEFT JOIN LATERAL (
    SELECT
      o_src.billing_account_id  AS src_billing_account_id,
      o_src.fatturazione_trigger AS src_fatturazione_trigger,
      o_src.uid                  AS src_ordine_uid,
      o_src.valuta_id            AS src_valuta_id,
      or_r.prezzo_unitario       AS src_prezzo_unitario
    FROM vendite.ordini_righe_fulfillment ful
    JOIN vendite.ordini_righe or_r ON or_r.id = ful.ordine_riga_id
    JOIN vendite.ordini o_src      ON o_src.id = or_r.ordine_id
    WHERE ful.ddt_riga_id = dr.id
    ORDER BY ful.id LIMIT 1
  ) src ON TRUE
  JOIN anagrafiche.billing_account ba
    ON ba.id = COALESCE(d.billing_account_id, src.src_billing_account_id)
  WHERE COALESCE(d.billing_account_id, src.src_billing_account_id) IS NOT NULL
    AND (
      (src.src_fatturazione_trigger IS NOT NULL
       AND src.src_fatturazione_trigger != 'CONFERMATO'
       AND sdd.codice_interno = src.src_fatturazione_trigger)
      OR
      (src.src_fatturazione_trigger IS NULL
       AND d.billing_account_id IS NOT NULL
       AND sdd.codice_interno IN ('SPEDITO', 'CONSEGNATO'))
    )
    AND (p_competenza_mese IS NULL OR date_trunc('month', d.data)::date = p_competenza_mese)
    AND (p_billing_account_id IS NULL
         OR COALESCE(d.billing_account_id, src.src_billing_account_id) = p_billing_account_id)
    AND (p_ddt_id IS NULL OR d.id = p_ddt_id)
    AND NOT EXISTS (
      SELECT 1 FROM vendite.commesse_attivita ca
      WHERE ca.segment_key = 'DDT:' || d.uid::text || ':R:' || dr.id::text
        AND ca.stato_emissione = 'EMESSA'
    )
  ORDER BY d.id, dr.id
  LIMIT p_limit;
END
$function$

COMMENT ON FUNCTION vendite.fn_list_ddt_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer, p_ddt_id bigint)
IS 'Lista righe DDT eligible al push su commessa (stato SPEDITO/CONSEGNATO o trigger specifico). uom_id da catalogo.articoli (canonica). p_ddt_id opzionale: NULL=batch globale, NOT NULL=singolo DDT. Filtri in AND. Esclude EMESSA via NOT EXISTS. rev 2026-06-28: sorgente/stato per codice_interno (analisi-hardcoded-codice §3a).';
```

---
{% include-markdown "signature-core.md" %}
