{% include-markdown "it/dbzero/vendite/manual/fn_list_ddt_da_pushare.md" %}
# ⚙️ Funzione `fn_list_ddt_da_pushare`

```sql
CREATE FUNCTION fn_list_ddt_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_list_ddt_da_pushare(p_competenza_mese date DEFAULT NULL::date, p_billing_account_id bigint DEFAULT NULL::bigint, p_limit integer DEFAULT NULL::integer)
 RETURNS TABLE(ddt_id bigint, ddt_uid uuid, riga_id bigint, billing_account_id bigint, utility_id integer, emittente_soggetto_ruolo_id bigint, competenza_dal date, competenza_al date, fatturazione_immediata boolean, sorgente_tipo_id bigint, sorgente_uid text, segment_key character varying, articolo_id uuid, istanza_utility_id bigint, data_attivita date, uom_id bigint, quantita numeric, qta_operativa numeric, uom_operativa_id bigint, factor_to_base numeric, competenza_mese date, prezzo_snapshot numeric, prezzo_bloccato boolean, pricing_mode character varying, tipo_movimento character varying, tipo_consumo character varying, valuta_id integer, meta jsonb)
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_sorgente_tipo_id config.sorgenti.id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Restituire le righe DDT pronte per il push su commessa,
  --   con tutti i campi necessari agli handler.
  --
  -- Due popolazioni:
  --   A. DDT da ordine (fulfillment esiste):
  --      - ordine.fatturazione_trigger IN ('SPEDITO','CONSEGNATO')
  --      - stato DDT deve corrispondere a ordine.fatturazione_trigger
  --      - prezzo da: COALESCE(ddt_righe.prezzo_unitario, ordini_righe.prezzo_unitario)
  --      - billing_account da: COALESCE(ddt.billing_account_id, ordini.billing_account_id)
  --
  --   B. DDT autonomo (nessun fulfillment):
  --      - ddt.billing_account_id IS NOT NULL (obbligatorio)
  --      - stato DDT IN ('SPEDITO','CONSEGNATO')
  --      - prezzo da ddt_righe.prezzo_unitario (puo` essere NULL; handler risolve)
  --
  -- Regole comuni:
  --   - riga attivo = TRUE
  --   - esclude righe con segment_key gia` EMESSA in commessa
  --   - prezzo_bloccato = TRUE se prezzo_snapshot presente
  --   - tipo_commessa target: AUTO, policy: DA_DOCUMENTO
  --
  -- NOTE:
  --   - uom_id non presente su ddt_righe: restituito NULL.
  --   - istanza_utility_id risolto da billing_account.
  --   - per DDT da ordine con evasione parziale, quantita = quantita
  --     effettiva della riga DDT (non la qta_evasa del fulfillment).
  --   - codice sorgente config.sorgenti: 'DDT_VENDITA' (id=8).
  -- =========================================================

  -- Lookup sorgente DDT_VENDITA attiva.
  SELECT s.id INTO v_sorgente_tipo_id
  FROM config.sorgenti s
  WHERE s.codice = 'DDT_VENDITA' AND s.attivo IS TRUE
  LIMIT 1;

  IF v_sorgente_tipo_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_list_ddt_da_pushare','E_GENERICO',
      jsonb_build_object(
        'scope','COMMESSE','severity','C','code','E_GENERICO',
        'lotto_id',NULL,'fattura_id',NULL,
        'context',jsonb_build_object('detail','sorgente DDT_VENDITA non configurata/attiva')
      ),
      NULL::uuid,
      'sorgente DDT_VENDITA non configurata/attiva'
    );
  END IF;

  RETURN QUERY
  SELECT
    d.id                                                              AS ddt_id,
    d.uid                                                             AS ddt_uid,
    dr.id                                                             AS riga_id,
    -- billing_account: da DDT diretto, oppure da ordine sorgente via fulfillment
    COALESCE(d.billing_account_id, src.src_billing_account_id)       AS billing_account_id,
    ba.utility_id,
    anagrafiche.fn_get_emittente_fiscale_id(
      COALESCE(d.billing_account_id, src.src_billing_account_id)
    )                                                                 AS emittente_soggetto_ruolo_id,
    d.data                                                            AS competenza_dal,
    d.data                                                            AS competenza_al,
    FALSE                                                             AS fatturazione_immediata,
    v_sorgente_tipo_id                                                AS sorgente_tipo_id,
    d.uid::text                                                       AS sorgente_uid,
    -- segment_key: stabile e deterministico per idempotenza upsert
    ('DDT:' || d.uid::text || ':R:' || dr.id::text)::varchar         AS segment_key,
    dr.articolo_id,
    ba.istanza_utility_id,
    d.data                                                            AS data_attivita,
    -- uom_id non presente su ddt_righe; handler deve risolvere se necessario
    NULL::bigint                                                      AS uom_id,
    -- quantita effettiva della riga DDT (consegna reale)
    dr.quantita,
    dr.qta_operativa,
    dr.uom_operativa_id,
    COALESCE(dr.factor_to_base, 1::numeric)                          AS factor_to_base,
    date_trunc('month', d.data)::date                                AS competenza_mese,
    -- prezzo: da DDT riga, oppure da ordine riga via fulfillment
    COALESCE(dr.prezzo_unitario, src.src_prezzo_unitario)            AS prezzo_snapshot,
    -- prezzo_bloccato se abbiamo un prezzo (da DDT o da ordine)
    (COALESCE(dr.prezzo_unitario, src.src_prezzo_unitario) IS NOT NULL)
                                                                      AS prezzo_bloccato,
    'FIXED'::varchar                                                  AS pricing_mode,
    'NORMALE'::varchar                                                AS tipo_movimento,
    'CONGUAGLIO'::varchar                                             AS tipo_consumo,
    COALESCE(d.valuta_id, src.src_valuta_id)                         AS valuta_id,
    jsonb_build_object(
      'ddt_numero',            d.numero,
      'ddt_anno',              d.anno,
      'ddt_serie',             d.serie,
      'ordine_sorgente_uid',   src.src_ordine_uid,
      'ordine_fatturaz_trg',   src.src_fatturazione_trigger,
      'tipo_commessa',         'AUTO',
      'policy_fatturazione',   'DA_DOCUMENTO'
    )                                                                 AS meta
  FROM vendite.ddt d
  JOIN config.stati_doc_ddt sdd
    ON sdd.id = d.stato_doc_ddt_id
  JOIN vendite.ddt_righe dr
    ON dr.ddt_id = d.id
   AND dr.attivo IS TRUE
  -- Subquery laterale: recupera dati ordine sorgente (al piu` 1 match per riga DDT).
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
    ORDER BY ful.id
    LIMIT 1
  ) src ON true
  -- Join billing_account per utility_id e istanza_utility_id.
  JOIN anagrafiche.billing_account ba
    ON ba.id = COALESCE(d.billing_account_id, src.src_billing_account_id)
  WHERE
    -- billing_account deve essere risolvibile (da DDT o da ordine).
    COALESCE(d.billing_account_id, src.src_billing_account_id) IS NOT NULL
    AND (
      -- Caso A: DDT da ordine — ordine dice di fatturare da DDT
      --   e stato DDT corrisponde al trigger dell'ordine.
      (src.src_fatturazione_trigger IS NOT NULL
        AND src.src_fatturazione_trigger != 'CONFERMATO'
        AND sdd.codice = src.src_fatturazione_trigger)
      OR
      -- Caso B: DDT autonomo (nessun fulfillment) — DDT in stato SPEDITO o CONSEGNATO.
      (src.src_fatturazione_trigger IS NULL
        AND d.billing_account_id IS NOT NULL
        AND sdd.codice IN ('SPEDITO', 'CONSEGNATO'))
    )
    -- Filtri opzionali.
    AND (p_competenza_mese IS NULL
         OR date_trunc('month', d.data)::date = p_competenza_mese)
    AND (p_billing_account_id IS NULL
         OR COALESCE(d.billing_account_id, src.src_billing_account_id) = p_billing_account_id)
    -- Esclude righe gia` emesse in commessa (ottimizzazione batch).
    AND NOT EXISTS (
      SELECT 1
      FROM vendite.commesse_attivita ca
      WHERE ca.segment_key = 'DDT:' || d.uid::text || ':R:' || dr.id::text
        AND ca.stato_emissione = 'EMESSA'
    )
  ORDER BY d.id, dr.id
  LIMIT p_limit;
END
$function$

COMMENT ON FUNCTION vendite.fn_list_ddt_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer)
IS 'Lista righe DDT eligible al push su commessa. Supporta due modalita`: (A) DDT da ordine con fatturazione_trigger SPEDITO/CONSEGNATO — prezzo e billing_account ereditati da ordine via fulfillment; (B) DDT autonomo — richiede billing_account_id e prezzo su DDT. utility_id/istanza_utility_id da billing_account. Prezzo bloccato se presente.';
```

---
{% include-markdown "signature-core.md" %}
