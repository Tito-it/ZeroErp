{% include-markdown "it/dbzero/vendite/manual/fn_list_ordini_da_pushare.md" %}
# ⚙️ Funzione `fn_list_ordini_da_pushare`

```sql
CREATE FUNCTION fn_list_ordini_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_list_ordini_da_pushare(p_competenza_mese date DEFAULT NULL::date, p_billing_account_id bigint DEFAULT NULL::bigint, p_limit integer DEFAULT NULL::integer)
 RETURNS TABLE(ordine_id bigint, ordine_uid uuid, riga_id bigint, billing_account_id bigint, utility_id integer, emittente_soggetto_ruolo_id bigint, competenza_dal date, competenza_al date, fatturazione_immediata boolean, sorgente_tipo_id bigint, sorgente_uid text, segment_key character varying, articolo_id uuid, istanza_utility_id bigint, data_attivita date, uom_id bigint, quantita numeric, qta_operativa numeric, uom_operativa_id bigint, factor_to_base numeric, competenza_mese date, prezzo_snapshot numeric, prezzo_bloccato boolean, pricing_mode character varying, tipo_movimento character varying, tipo_consumo character varying, valuta_id integer, meta jsonb)
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_sorgente_tipo_id    config.sorgenti.id%TYPE;
  v_stato_confermato_id config.stati_doc_ordini.id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Restituire le righe ordine pronte per il push su
  --   commessa, con tutti i campi necessari agli handler.
  --
  -- Regole:
  --   - stato documento CONFERMATO (codice da config.stati_doc_ordini)
  --   - fatturazione_trigger = 'CONFERMATO' (ordini con trigger
  --     SPEDITO/CONSEGNATO sono delegati al push DDT)
  --   - riga attivo = TRUE, quantita > 0, prezzo >= 0
  --   - esclude righe con segment_key gia` EMESSA in commessa
  --   - prezzo_bloccato = TRUE (ordini sempre bloccati alla conferma)
  --   - utility_id e istanza_utility_id risolti da billing_account
  --   - tipo_commessa target: AUTO, policy: DA_DOCUMENTO
  --
  -- NOTE:
  --   - uom_id non presente su ordini_righe: restituito NULL;
  --     recuperare da catalogo.articoli_uom_operativa se necessario.
  --   - competenza_dal/al = o.data (nessuna validita` su ordini).
  --   - fatturazione_immediata = FALSE (ordini non hanno fatturazione diretta).
  -- =========================================================

  -- Lookup sorgente ORDINE_VENDITA attiva.
  SELECT s.id INTO v_sorgente_tipo_id
  FROM config.sorgenti s
  WHERE s.codice = 'ORDINE_VENDITA' AND s.attivo IS TRUE
  LIMIT 1;

  IF v_sorgente_tipo_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_list_ordini_da_pushare','E_GENERICO',
      jsonb_build_object(
        'scope','COMMESSE','severity','C','code','E_GENERICO',
        'lotto_id',NULL,'fattura_id',NULL,
        'context',jsonb_build_object('detail','sorgente ORDINE_VENDITA non configurata/attiva')
      ),
      NULL::uuid,
      'sorgente ORDINE_VENDITA non configurata/attiva'
    );
  END IF;

  -- Lookup stato documento CONFERMATO.
  SELECT s.id INTO v_stato_confermato_id
  FROM config.stati_doc_ordini s
  WHERE s.codice = 'CONFERMATO' AND s.attivo IS TRUE
  LIMIT 1;

  RETURN QUERY
  SELECT
    o.id                                                           AS ordine_id,
    o.uid                                                          AS ordine_uid,
    or_r.id                                                        AS riga_id,
    o.billing_account_id,
    ba.utility_id,
    anagrafiche.fn_get_emittente_fiscale_id(o.billing_account_id) AS emittente_soggetto_ruolo_id,
    -- Ordini non hanno validita_dal/al: si usa la data ordine.
    o.data                                                         AS competenza_dal,
    o.data                                                         AS competenza_al,
    FALSE                                                          AS fatturazione_immediata,
    v_sorgente_tipo_id                                             AS sorgente_tipo_id,
    o.uid::text                                                    AS sorgente_uid,
    -- segment_key: stabile e deterministico per idempotenza upsert
    ('ORD:' || o.uid::text || ':R:' || or_r.id::text)::varchar    AS segment_key,
    or_r.articolo_id,
    ba.istanza_utility_id,
    o.data                                                         AS data_attivita,
    -- uom_id non presente su ordini_righe; handler deve risolvere se necessario
    NULL::bigint                                                   AS uom_id,
    or_r.quantita,
    or_r.qta_operativa,
    or_r.uom_operativa_id,
    COALESCE(or_r.factor_to_base, 1::numeric)                     AS factor_to_base,
    date_trunc('month', o.data)::date                             AS competenza_mese,
    or_r.prezzo_unitario                                           AS prezzo_snapshot,
    -- Ordini: prezzo sempre bloccato alla conferma.
    TRUE                                                           AS prezzo_bloccato,
    'FIXED'::varchar                                               AS pricing_mode,
    'NORMALE'::varchar                                             AS tipo_movimento,
    'CONGUAGLIO'::varchar                                          AS tipo_consumo,
    o.valuta_id,
    jsonb_build_object(
      'ordine_numero',       o.numero,
      'ordine_anno',         o.anno,
      'ordine_serie',        o.serie,
      'tipo_commessa',       'AUTO',
      'policy_fatturazione', 'DA_DOCUMENTO'
    )                                                              AS meta
  FROM vendite.ordini o
  JOIN anagrafiche.billing_account ba
    ON ba.id = o.billing_account_id
  JOIN vendite.ordini_righe or_r
    ON or_r.ordine_id = o.id
   AND or_r.attivo IS TRUE
   AND or_r.quantita > 0
   AND or_r.prezzo_unitario >= 0
  WHERE o.billing_account_id IS NOT NULL
    -- Stato documento: CONFERMATO (NULL = configurazione mancante, non filtra).
    AND (v_stato_confermato_id IS NULL OR o.stato_doc_ordine_id = v_stato_confermato_id)
    -- Solo ordini con fatturazione alla conferma.
    -- Ordini con SPEDITO/CONSEGNATO sono delegati a fn_list_ddt_da_pushare.
    AND o.fatturazione_trigger = 'CONFERMATO'
    -- Filtri opzionali.
    AND (p_competenza_mese IS NULL
         OR date_trunc('month', o.data)::date = p_competenza_mese)
    AND (p_billing_account_id IS NULL OR o.billing_account_id = p_billing_account_id)
    -- Esclude righe gia` emesse in commessa (ottimizzazione batch).
    AND NOT EXISTS (
      SELECT 1
      FROM vendite.commesse_attivita ca
      WHERE ca.segment_key = 'ORD:' || o.uid::text || ':R:' || or_r.id::text
        AND ca.stato_emissione = 'EMESSA'
    )
  ORDER BY o.id, or_r.id
  LIMIT p_limit;
END
$function$

COMMENT ON FUNCTION vendite.fn_list_ordini_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer)
IS 'Lista righe ordine eligible al push su commessa (stato CONFERMATO, fatturazione_trigger CONFERMATO). Ordini con trigger SPEDITO/CONSEGNATO sono delegati a fn_list_ddt_da_pushare. Restituisce tutti i campi per get_or_create_commessa + upsert_commessa_attivita. utility_id/istanza_utility_id risolti da billing_account. Prezzo sempre bloccato.';
```

---
{% include-markdown "signature-core.md" %}
