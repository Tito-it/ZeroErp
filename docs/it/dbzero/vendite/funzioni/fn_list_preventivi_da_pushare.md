{% include-markdown "it/dbzero/vendite/manual/fn_list_preventivi_da_pushare.md" %}
# ⚙️ Funzione `fn_list_preventivi_da_pushare`

```sql
CREATE FUNCTION fn_list_preventivi_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer, p_preventivo_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_list_preventivi_da_pushare(p_competenza_mese date DEFAULT NULL::date, p_billing_account_id bigint DEFAULT NULL::bigint, p_limit integer DEFAULT NULL::integer, p_preventivo_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(preventivo_id bigint, preventivo_uid uuid, riga_id bigint, billing_account_id bigint, utility_id integer, emittente_soggetto_ruolo_id bigint, competenza_dal date, competenza_al date, fatturazione_immediata boolean, sorgente_tipo_id bigint, sorgente_uid text, segment_key character varying, articolo_id uuid, istanza_utility_id bigint, data_attivita date, uom_id bigint, quantita numeric, qta_operativa numeric, uom_operativa_id bigint, factor_to_base numeric, competenza_mese date, prezzo_snapshot numeric, prezzo_bloccato boolean, pricing_mode character varying, tipo_movimento character varying, tipo_consumo character varying, valuta_id integer, meta jsonb, tipo_doc_fiscale_id bigint)
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_sorgente_tipo_id    config.sorgenti.id%TYPE;
  v_tipo_doc_fiscale_id config.sorgenti.tipo_doc_fiscale_id%TYPE;
  v_stato_accettato_id  config.stati_doc_preventivi.id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Restituire le righe preventivo pronte per il push su
  --   commessa, con tutti i campi necessari agli handler.
  --
  -- Regole:
  --   - stato documento ACCETTATO
  --   - SOLO righe natura destinazione_tipo='COMMESSA' (natura NULL
  --     trattata come COMMESSA: pregresso pre-trigger). La merce
  --     (ORDINE) va su fn_push_preventivo_a_ordine, non qui.
  --   - esclude righe gia` EMESSA in commessa (via NOT EXISTS)
  --   - riga attivo = true, quantita > 0, prezzo >= 0
  --   - prezzo_bloccato = fatturazione_immediata
  --   - tipo_commessa target: REALE, policy: DA_DOCUMENTO
  --
  -- Competenza (rev 10-06-2026, brief competenza):
  --   - competenza_dal/al NON nulli (commesse_attivita NOT NULL):
  --     fallback validita -> competenza_mese -> data. GREATEST su
  --     competenza_al garantisce dal<=al anche con validita_dal
  --     NULL + validita_al valorizzato.
  --   - competenza_mese: policy p.competenza_mese autorevole, con
  --     fallback al derivato validita/data per il pregresso.
  --   - competenza_dal/al = periodo attivita'; competenza_mese =
  --     mese di fatturazione (policy). Indipendenti per costruzione.
  --
  -- Estensione 2026-05: p_preventivo_id (opzionale):
  --   NULL = lista globale batch; NOT NULL = singolo preventivo UI-driven.
  --
  -- NOTE:
  --   - uom_id: UoM canonica da catalogo.articoli (JOIN su pr.articolo_id).
  --     La colonna preventivi_righe.uom_id e` droppata (non usare).
  --   - uom_operativa_id: UoM di inserimento operatore (dalla riga).
  --   - natura: LEFT JOIN per non perdere righe a natura NULL.
  -- =========================================================

  IF p_preventivo_id IS NOT NULL AND p_preventivo_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_list_preventivi_da_pushare', 'E_PUSH_SORGENTE_ID_INVALIDO',
      jsonb_build_object('parametro', 'p_preventivo_id', 'valore', p_preventivo_id),
      NULL::uuid,
      'p_preventivo_id', p_preventivo_id::text
    );
  END IF;

  SELECT s.id, s.tipo_doc_fiscale_id
    INTO v_sorgente_tipo_id, v_tipo_doc_fiscale_id
  FROM config.sorgenti s
  WHERE s.codice = 'PREVENTIVO' AND s.attivo IS TRUE LIMIT 1;

  IF v_sorgente_tipo_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_list_preventivi_da_pushare', 'E_CODICE',
      jsonb_build_object('codice', 'PREVENTIVO'),
      NULL::uuid, 'PREVENTIVO', 'config.sorgenti'
    );
  END IF;

  SELECT s.id INTO v_stato_accettato_id
  FROM config.stati_doc_preventivi s
  WHERE s.codice = 'ACCETTATO' AND s.attivo IS TRUE LIMIT 1;

  RETURN QUERY
  SELECT
    p.id                                                          AS preventivo_id,
    p.uid                                                         AS preventivo_uid,
    pr.id                                                         AS riga_id,
    p.billing_account_id,
    p.utility_id,
    anagrafiche.fn_get_emittente_fiscale_id(p.billing_account_id) AS emittente_soggetto_ruolo_id,
    -- competenza_dal/al NOT NULL-safe (brief competenza 10-06-2026)
    COALESCE(p.validita_dal, p.competenza_mese, p.data)           AS competenza_dal,
    GREATEST(
      COALESCE(p.validita_dal, p.competenza_mese, p.data),
      COALESCE(p.validita_al, p.validita_dal, p.competenza_mese, p.data)
    )                                                             AS competenza_al,
    p.fatturazione_immediata,
    v_sorgente_tipo_id                                            AS sorgente_tipo_id,
    p.uid::text                                                   AS sorgente_uid,
    ('PREV:' || p.uid::text || ':R:' || pr.id::text)::varchar     AS segment_key,
    pr.articolo_id,
    p.istanza_utility_id,
    COALESCE(p.validita_dal, p.data)                             AS data_attivita,
    -- uom_id canonica da catalogo.articoli (fix bug proiezione NULL)
    a.uom_id,
    pr.quantita,
    pr.qta_operativa,
    pr.uom_operativa_id,
    COALESCE(pr.factor_to_base, 1::numeric)                      AS factor_to_base,
    -- competenza_mese: policy autorevole, fallback al derivato (pregresso)
    COALESCE(
      p.competenza_mese,
      date_trunc('month', COALESCE(p.validita_dal, p.data))::date
    )                                                             AS competenza_mese,
    pr.prezzo_unitario                                            AS prezzo_snapshot,
    COALESCE(p.fatturazione_immediata, false)                    AS prezzo_bloccato,
    'FIXED'::varchar                                              AS pricing_mode,
    'NORMALE'::varchar                                            AS tipo_movimento,
    'CONGUAGLIO'::varchar                                         AS tipo_consumo,
    p.valuta_id,
    jsonb_build_object(
      'preventivo_numero',   p.numero,
      'preventivo_rev',      p.rev,
      'tipo_commessa',       'REALE',
      'policy_fatturazione', 'DA_DOCUMENTO'
    )                                                             AS meta,
    v_tipo_doc_fiscale_id                                         AS tipo_doc_fiscale_id
  FROM vendite.preventivi p
  JOIN vendite.preventivi_righe pr
    ON pr.preventivo_id = p.id
   AND pr.attivo IS TRUE
   AND pr.quantita > 0
   AND pr.prezzo_unitario >= 0
  JOIN catalogo.articoli a ON a.id = pr.articolo_id
  -- Natura di riga: LEFT JOIN per non perdere le righe a natura NULL.
  LEFT JOIN config.nature_vendita nv ON nv.id = pr.natura_vendita_id
  WHERE p.billing_account_id IS NOT NULL
    AND p.utility_id IS NOT NULL
    AND (v_stato_accettato_id IS NULL OR p.stato_doc_preventivo_id = v_stato_accettato_id)
    -- SOLO righe destinate a COMMESSA (natura NULL = pregresso -> COMMESSA).
    -- La merce (ORDINE) e' esclusa: va su fn_push_preventivo_a_ordine.
    AND (pr.natura_vendita_id IS NULL OR nv.destinazione_tipo = 'COMMESSA')
    -- Filtro allineato alla stessa espressione del SELECT competenza_mese.
    AND (p_competenza_mese IS NULL
         OR COALESCE(
              p.competenza_mese,
              date_trunc('month', COALESCE(p.validita_dal, p.data))::date
            ) = p_competenza_mese)
    AND (p_billing_account_id IS NULL OR p.billing_account_id = p_billing_account_id)
    AND (p_preventivo_id IS NULL OR p.id = p_preventivo_id)
    AND NOT EXISTS (
      SELECT 1 FROM vendite.commesse_attivita ca
      WHERE ca.segment_key = 'PREV:' || p.uid::text || ':R:' || pr.id::text
        AND ca.stato_emissione = 'EMESSA'
    )
  ORDER BY p.id, pr.id
  LIMIT p_limit;
END
$function$

COMMENT ON FUNCTION vendite.fn_list_preventivi_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer, p_preventivo_id bigint)
IS 'Lista righe preventivo eligible al push su commessa (stato ACCETTATO). NATURA-AWARE (rev 09-06-2026): solo righe con natura destinazione_tipo=COMMESSA (natura NULL = pregresso, inclusa); la merce (ORDINE) va su fn_push_preventivo_a_ordine. uom_id da catalogo.articoli (canonica). COMPETENZA (rev 10-06-2026): competenza_dal/al NOT NULL-safe (COALESCE validita/competenza_mese/data + GREATEST dal<=al), competenza_mese policy-aware (COALESCE(competenza_mese, derivato)); filtro WHERE allineato. p_preventivo_id opzionale: NULL=batch globale, NOT NULL=UI push singolo. Filtri in AND. Esclude EMESSA via NOT EXISTS.';
```

---
{% include-markdown "signature-core.md" %}
