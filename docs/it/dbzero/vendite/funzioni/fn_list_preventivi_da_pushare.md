{% include-markdown "it/dbzero/vendite/manual/fn_list_preventivi_da_pushare.md" %}
# ⚙️ Funzione `fn_list_preventivi_da_pushare`

```sql
CREATE FUNCTION fn_list_preventivi_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_list_preventivi_da_pushare(p_competenza_mese date DEFAULT NULL::date, p_billing_account_id bigint DEFAULT NULL::bigint, p_limit integer DEFAULT NULL::integer)
 RETURNS TABLE(preventivo_id bigint, preventivo_uid uuid, riga_id bigint, billing_account_id bigint, utility_id integer, emittente_soggetto_ruolo_id bigint, competenza_dal date, competenza_al date, fatturazione_immediata boolean, sorgente_tipo_id bigint, sorgente_uid text, segment_key character varying, articolo_id uuid, istanza_utility_id bigint, data_attivita date, uom_id bigint, quantita numeric, qta_operativa numeric, uom_operativa_id bigint, factor_to_base numeric, competenza_mese date, prezzo_snapshot numeric, prezzo_bloccato boolean, pricing_mode character varying, tipo_movimento character varying, tipo_consumo character varying, valuta_id integer, meta jsonb)
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_sorgente_tipo_id   config.sorgenti.id%TYPE;
  v_stato_accettato_id config.stati_doc_preventivi.id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Restituire le righe preventivo pronte per il push su
  --   commessa, con tutti i campi necessari agli handler.
  --
  -- Regole:
  --   - stato documento ACCETTATO (codice da config.stati_doc_preventivi)
  --   - esclude righe gia` EMESSA in commessa (via NOT EXISTS)
  --   - riga attivo = true, quantita > 0, prezzo >= 0
  --   - esclude righe con segment_key gia` EMESSA in commessa
  --   - prezzo_bloccato = fatturazione_immediata (documento)
  --   - tipo_commessa target: REALE, policy: DA_DOCUMENTO
  --
  -- NOTE:
  --   - preventivi_righe.uom_id e` stata droppata (mai popolata dal trigger);
  --     restituito NULL::bigint.
  -- =========================================================

  -- Lookup sorgente PREVENTIVO attiva.
  SELECT s.id INTO v_sorgente_tipo_id
  FROM config.sorgenti s
  WHERE s.codice = 'PREVENTIVO' AND s.attivo IS TRUE
  LIMIT 1;

  IF v_sorgente_tipo_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_list_preventivi_da_pushare','E_GENERICO',
      jsonb_build_object(
        'scope','COMMESSE','severity','C','code','E_GENERICO',
        'lotto_id',NULL,'fattura_id',NULL,
        'context',jsonb_build_object('detail','sorgente PREVENTIVO non configurata/attiva')
      ),
      NULL::uuid,
      'sorgente PREVENTIVO non configurata/attiva'
    );
  END IF;

  -- Lookup stato documento ACCETTATO.
  SELECT s.id INTO v_stato_accettato_id
  FROM config.stati_doc_preventivi s
  WHERE s.codice = 'ACCETTATO' AND s.attivo IS TRUE
  LIMIT 1;

  RETURN QUERY
  SELECT
    p.id                                                          AS preventivo_id,
    p.uid                                                         AS preventivo_uid,
    pr.id                                                         AS riga_id,
    p.billing_account_id,
    p.utility_id,
    anagrafiche.fn_get_emittente_fiscale_id(p.billing_account_id) AS emittente_soggetto_ruolo_id,
    p.validita_dal                                                AS competenza_dal,
    p.validita_al                                                 AS competenza_al,
    p.fatturazione_immediata,
    v_sorgente_tipo_id                                            AS sorgente_tipo_id,
    p.uid::text                                                   AS sorgente_uid,
    -- segment_key: stabile e deterministico per idempotenza upsert
    ('PREV:' || p.uid::text || ':R:' || pr.id::text)::varchar    AS segment_key,
    pr.articolo_id,
    p.istanza_utility_id,
    COALESCE(p.validita_dal, p.data)                             AS data_attivita,
    -- uom_id rimosso da preventivi_righe (colonna droppata, mai valorizzata)
    NULL::bigint                                                  AS uom_id,
    pr.quantita,
    pr.qta_operativa,
    pr.uom_operativa_id,
    COALESCE(pr.factor_to_base, 1::numeric)                      AS factor_to_base,
    date_trunc('month', COALESCE(p.validita_dal, p.data))::date  AS competenza_mese,
    pr.prezzo_unitario                                            AS prezzo_snapshot,
    -- prezzo_bloccato = true solo per fatturazione immediata;
    -- per periodica rimane ricalcolabile al momento del pull.
    COALESCE(p.fatturazione_immediata, false)                    AS prezzo_bloccato,
    'FIXED'::varchar                                              AS pricing_mode,
    'NORMALE'::varchar                                            AS tipo_movimento,
    'CONGUAGLIO'::varchar                                         AS tipo_consumo,
    p.valuta_id,
    jsonb_build_object(
      'preventivo_numero',  p.numero,
      'preventivo_rev',     p.rev,
      'tipo_commessa',      'REALE',
      'policy_fatturazione','DA_DOCUMENTO'
    )                                                             AS meta
  FROM vendite.preventivi p
  JOIN vendite.preventivi_righe pr
    ON pr.preventivo_id = p.id
   AND pr.attivo IS TRUE
   AND pr.quantita > 0
   AND pr.prezzo_unitario >= 0
  WHERE p.billing_account_id IS NOT NULL
    AND p.utility_id IS NOT NULL
    -- Stato documento: ACCETTATO (NULL = configurazione mancante, non filtra).
    AND (v_stato_accettato_id IS NULL OR p.stato_doc_preventivo_id = v_stato_accettato_id)
    -- Filtri opzionali.
    AND (p_competenza_mese IS NULL
         OR date_trunc('month', COALESCE(p.validita_dal, p.data))::date = p_competenza_mese)
    AND (p_billing_account_id IS NULL OR p.billing_account_id = p_billing_account_id)
    -- Esclude righe gia` emesse in commessa (ottimizzazione batch).
    AND NOT EXISTS (
      SELECT 1
      FROM vendite.commesse_attivita ca
      WHERE ca.segment_key = 'PREV:' || p.uid::text || ':R:' || pr.id::text
        AND ca.stato_emissione = 'EMESSA'
    )
  ORDER BY p.id, pr.id
  LIMIT p_limit;
END
$function$

COMMENT ON FUNCTION vendite.fn_list_preventivi_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer)
IS 'Lista righe preventivo eligible al push su commessa (stato ACCETTATO). Restituisce tutti i campi per get_or_create_commessa + upsert_commessa_attivita. Esclude righe gia` emesse via NOT EXISTS su commesse_attivita.';
```

---
{% include-markdown "signature-core.md" %}
