{% include-markdown "it/dbzero/vendite/manual/fn_list_ordini_da_pushare.md" %}
# ⚙️ Funzione `fn_list_ordini_da_pushare`

```sql
CREATE FUNCTION fn_list_ordini_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer, p_ordine_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_list_ordini_da_pushare(p_competenza_mese date DEFAULT NULL::date, p_billing_account_id bigint DEFAULT NULL::bigint, p_limit integer DEFAULT NULL::integer, p_ordine_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(ordine_id bigint, ordine_uid uuid, riga_id bigint, billing_account_id bigint, utility_id integer, emittente_soggetto_ruolo_id bigint, competenza_dal date, competenza_al date, fatturazione_immediata boolean, sorgente_tipo_id bigint, sorgente_uid text, segment_key character varying, articolo_id uuid, istanza_utility_id bigint, data_attivita date, uom_id bigint, quantita numeric, qta_operativa numeric, uom_operativa_id bigint, factor_to_base numeric, competenza_mese date, prezzo_snapshot numeric, prezzo_bloccato boolean, pricing_mode character varying, tipo_movimento character varying, tipo_consumo character varying, valuta_id integer, meta jsonb, tipo_doc_fiscale_id bigint)
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_sorgente_tipo_id    config.sorgenti.id%TYPE;
  v_tipo_doc_fiscale_id config.sorgenti.tipo_doc_fiscale_id%TYPE;
  v_stato_confermato_id config.stati_doc_ordini.id%TYPE;
BEGIN
  -- rev 2026-06-28 (analisi-hardcoded-codice §3a): sorgente/stato
  -- risolti per codice_interno (immutabile), non per codice (mutabile).
  IF p_ordine_id IS NOT NULL AND p_ordine_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_list_ordini_da_pushare', 'E_PUSH_SORGENTE_ID_INVALIDO',
      jsonb_build_object('parametro', 'p_ordine_id', 'valore', p_ordine_id),
      NULL::uuid,
      'p_ordine_id', p_ordine_id::text
    );
  END IF;

  SELECT s.id, s.tipo_doc_fiscale_id
    INTO v_sorgente_tipo_id, v_tipo_doc_fiscale_id
  FROM config.sorgenti s
  WHERE s.codice_interno = 'ORDINE_VENDITA' AND s.attivo IS TRUE LIMIT 1;

  IF v_sorgente_tipo_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_list_ordini_da_pushare', 'E_CODICE',
      jsonb_build_object('codice', 'ORDINE_VENDITA'),
      NULL::uuid, 'ORDINE_VENDITA', 'config.sorgenti'
    );
  END IF;

  SELECT s.id INTO v_stato_confermato_id
  FROM config.stati_doc_ordini s
  WHERE s.codice_interno = 'CONFERMATO' AND s.attivo IS TRUE LIMIT 1;

  RETURN QUERY
  SELECT
    o.id, o.uid, or_r.id,
    o.billing_account_id,
    ba.utility_id,
    anagrafiche.fn_get_emittente_fiscale_id(o.billing_account_id),
    o.data, o.data,
    FALSE,
    v_sorgente_tipo_id,
    o.uid::text,
    ('ORD:' || o.uid::text || ':R:' || or_r.id::text)::varchar,
    or_r.articolo_id,
    ba.istanza_utility_id,
    o.data,
    -- uom_id canonica da catalogo.articoli (fix bug proiezione NULL)
    a.uom_id,
    or_r.quantita,
    or_r.qta_operativa,
    or_r.uom_operativa_id,
    COALESCE(or_r.factor_to_base, 1::numeric),
    date_trunc('month', o.data)::date,
    or_r.prezzo_unitario,
    TRUE,
    'FIXED'::varchar,
    'NORMALE'::varchar,
    'CONGUAGLIO'::varchar,
    o.valuta_id,
    jsonb_build_object(
      'ordine_numero',       o.numero,
      'ordine_anno',         o.anno,
      'ordine_serie',        o.serie,
      'tipo_commessa',       'AUTO',
      'policy_fatturazione', 'DA_DOCUMENTO'
    ),
    v_tipo_doc_fiscale_id
  FROM vendite.ordini o
  JOIN anagrafiche.billing_account ba ON ba.id = o.billing_account_id
  JOIN vendite.ordini_righe or_r
    ON or_r.ordine_id = o.id
   AND or_r.attivo IS TRUE
   AND or_r.quantita > 0
   AND or_r.prezzo_unitario >= 0
  JOIN catalogo.articoli a ON a.id = or_r.articolo_id
  WHERE o.billing_account_id IS NOT NULL
    AND (v_stato_confermato_id IS NULL OR o.stato_doc_ordine_id = v_stato_confermato_id)
    AND o.fatturazione_trigger = 'CONFERMATO'
    AND (p_competenza_mese IS NULL OR date_trunc('month', o.data)::date = p_competenza_mese)
    AND (p_billing_account_id IS NULL OR o.billing_account_id = p_billing_account_id)
    AND (p_ordine_id IS NULL OR o.id = p_ordine_id)
    AND NOT EXISTS (
      SELECT 1 FROM vendite.commesse_attivita ca
      WHERE ca.segment_key = 'ORD:' || o.uid::text || ':R:' || or_r.id::text
        AND ca.stato_emissione = 'EMESSA'
    )
  ORDER BY o.id, or_r.id
  LIMIT p_limit;
END
$function$

COMMENT ON FUNCTION vendite.fn_list_ordini_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer, p_ordine_id bigint)
IS 'Lista righe ordine eligible al push su commessa (stato CONFERMATO, fatturazione_trigger CONFERMATO). uom_id da catalogo.articoli (canonica). p_ordine_id opzionale: NULL=batch globale, NOT NULL=singolo ordine. Filtri in AND. Esclude EMESSA via NOT EXISTS. rev 2026-06-28: sorgente/stato per codice_interno (analisi-hardcoded-codice §3a).';
```

---
{% include-markdown "signature-core.md" %}
