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
  -- =========================================================
  -- Scopo:
  --   Restituire le righe contratto pronte per il push su
  --   commessa, con tutti i campi necessari agli handler.
  --
  -- Regole:
  --   - stato documento ATTIVO (codice da config.stati_doc_contratti)
  --   - contratto in validita` (valido_al IS NULL o >= competenza_mese/oggi)
  --   - riga attivo = TRUE, articolo_id NOT NULL
  --   - esclude righe con segment_key gia` EMESSA in commessa
  --   - prezzo_bloccato = TRUE se prezzo_unitario presente
  --   - utility_id e istanza_utility_id direttamente da contratti
  --   - tipo_commessa target: AUTO, policy: DA_DOCUMENTO
  --
  -- NOTE:
  --   - uom_id non presente su contratti_righe: restituito NULL;
  --     recuperare da catalogo.articoli_uom_operativa se necessario.
  --   - quantita = quantita_fissa (puo` essere NULL se sorgente
  --     non ha quantita` definita; l'handler deve risolvere).
  --   - valuta_id non presente su contratti: restituito NULL;
  --     l'handler deve risolvere da billing_account o config.
  --   - Per contratti con righe ricorrenti (periodicita` != NULL),
  --     il segment_key include il mese di competenza per
  --     garantire idempotenza su piu` periodi.
  --   - codice sorgente config.sorgenti: 'CONTRATTO' (id=4).
  -- =========================================================

  -- Lookup sorgente CONTRATTO attiva + tipo_doc_fiscale_id (§26 B+D).
  SELECT s.id, s.tipo_doc_fiscale_id
    INTO v_sorgente_tipo_id, v_tipo_doc_fiscale_id
  FROM config.sorgenti s
  WHERE s.codice = 'CONTRATTO' AND s.attivo IS TRUE
  LIMIT 1;

  IF v_sorgente_tipo_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_list_contratti_da_pushare','E_GENERICO',
      jsonb_build_object(
        'scope','COMMESSE','severity','C','code','E_GENERICO',
        'lotto_id',NULL,'fattura_id',NULL,
        'context',jsonb_build_object('detail','sorgente CONTRATTO non configurata/attiva')
      ),
      NULL::uuid,
      'sorgente CONTRATTO non configurata/attiva'
    );
  END IF;

  -- Lookup stato documento ATTIVO.
  SELECT s.id INTO v_stato_attivo_id
  FROM config.stati_doc_contratti s
  WHERE s.codice = 'ATTIVO' AND s.attivo IS TRUE
  LIMIT 1;

  RETURN QUERY
  SELECT
    c.id                                                            AS contratto_id,
    c.uid                                                           AS contratto_uid,
    cr.id                                                           AS riga_id,
    c.billing_account_id,
    c.utility_id,
    anagrafiche.fn_get_emittente_fiscale_id(c.billing_account_id)  AS emittente_soggetto_ruolo_id,
    c.valido_dal                                                    AS competenza_dal,
    c.valido_al                                                     AS competenza_al,
    FALSE                                                           AS fatturazione_immediata,
    v_sorgente_tipo_id                                              AS sorgente_tipo_id,
    c.uid::text                                                     AS sorgente_uid,
    -- segment_key: include competenza_mese per idempotenza su piu` periodi.
    -- Per righe ricorrenti lo stesso contratto puo` pushare per mesi diversi.
    ('CONTR:' || c.uid::text || ':R:' || cr.id::text
      || ':M:' || to_char(
        date_trunc('month', COALESCE(c.valido_dal, c.data))::date,
        'YYYY-MM'
      )
    )::varchar                                                      AS segment_key,
    cr.articolo_id,
    c.istanza_utility_id,
    COALESCE(c.valido_dal, c.data)                                 AS data_attivita,
    -- uom_id non presente su contratti_righe; handler deve risolvere se necessario
    NULL::bigint                                                    AS uom_id,
    -- quantita_fissa come quantita (puo` essere NULL; handler valida)
    cr.quantita_fissa                                               AS quantita,
    cr.qta_operativa,
    cr.uom_operativa_id,
    COALESCE(cr.factor_to_base, 1::numeric)                        AS factor_to_base,
    date_trunc('month', COALESCE(c.valido_dal, c.data))::date      AS competenza_mese,
    cr.prezzo_unitario                                              AS prezzo_snapshot,
    -- prezzo_bloccato = TRUE se prezzo_unitario presente (contratto definisce il prezzo)
    (cr.prezzo_unitario IS NOT NULL)                               AS prezzo_bloccato,
    'FIXED'::varchar                                                AS pricing_mode,
    'NORMALE'::varchar                                              AS tipo_movimento,
    -- tipo_consumo varia in base a tipo_erogazione della riga
    COALESCE(cr.tipo_erogazione, 'CANONE')::varchar               AS tipo_consumo,
    -- valuta_id non disponibile su contratti; handler deve risolvere
    NULL::integer                                                   AS valuta_id,
    jsonb_build_object(
      'contratto_numero',     c.numero,
      'periodicita',          cr.periodicita,
      'generazione_canone',   cr.generazione_canone,
      'competenza_canone',    cr.competenza_canone,
      'tipo_erogazione',      cr.tipo_erogazione,
      'tipo_commessa',        'AUTO',
      'policy_fatturazione',  'DA_DOCUMENTO'
    )                                                               AS meta,
    v_tipo_doc_fiscale_id                                             AS tipo_doc_fiscale_id
  FROM vendite.contratti c
  JOIN vendite.contratti_righe cr
    ON cr.contratto_id = c.id
   AND COALESCE(cr.attivo, true) IS TRUE
  WHERE c.billing_account_id IS NOT NULL
    -- Stato documento: ATTIVO (NULL = configurazione mancante, non filtra).
    AND (v_stato_attivo_id IS NULL OR c.stato_doc_contratto_id = v_stato_attivo_id)
    -- Contratto in validita` (non scaduto).
    AND (c.valido_al IS NULL OR c.valido_al >= COALESCE(p_competenza_mese, CURRENT_DATE))
    -- Filtri opzionali.
    AND (p_competenza_mese IS NULL
         OR date_trunc('month', COALESCE(c.valido_dal, c.data))::date = p_competenza_mese)
    AND (p_billing_account_id IS NULL OR c.billing_account_id = p_billing_account_id)
    -- Esclude righe gia` emesse in commessa (ottimizzazione batch).
    AND NOT EXISTS (
      SELECT 1
      FROM vendite.commesse_attivita ca
      WHERE ca.segment_key = 'CONTR:' || c.uid::text || ':R:' || cr.id::text
        || ':M:' || to_char(
          date_trunc('month', COALESCE(c.valido_dal, c.data))::date,
          'YYYY-MM'
        )
        AND ca.stato_emissione = 'EMESSA'
    )
  ORDER BY c.id, cr.id
  LIMIT p_limit;
END
$function$

COMMENT ON FUNCTION vendite.fn_list_contratti_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer)
IS 'Lista righe contratto eligible al push su commessa (stato ATTIVO, in validita`). Restituisce tutti i campi per get_or_create_commessa + upsert_commessa_attivita. segment_key include competenza_mese per idempotenza su periodi diversi. uom_id e valuta_id NULL: risolti dall''handler. Predisposizione base.';
```

---
{% include-markdown "signature-core.md" %}
