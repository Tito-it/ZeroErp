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
  -- rev 2026-06-28: sorgente/stato DDT per codice_interno (immutabile).
  -- rev 2026-07-17 (step 3): proietta la differenza del contatore.
  -- rev 2026-07-18 (step 5): eleggibilita' dallo stato-trigger IN POI.
  -- rev 2026-07-18 (step 5b): esclude le causali non fatturabili.
  IF p_ddt_id IS NOT NULL AND p_ddt_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_list_ddt_da_pushare', 'E_PUSH_SORGENTE_ID_INVALIDO',
      jsonb_build_object('parametro', 'p_ddt_id', 'valore', p_ddt_id),
      NULL::uuid, 'p_ddt_id', p_ddt_id::text);
  END IF;

  SELECT s.id, s.tipo_doc_fiscale_id
    INTO v_sorgente_tipo_id, v_tipo_doc_fiscale_id
  FROM config.sorgenti s
  WHERE s.codice_interno = 'DDT_VENDITA' AND s.attivo IS TRUE LIMIT 1;

  IF v_sorgente_tipo_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_list_ddt_da_pushare', 'E_CODICE',
      jsonb_build_object('codice', 'DDT_VENDITA'),
      NULL::uuid, 'DDT_VENDITA', 'config.sorgenti');
  END IF;

  RETURN QUERY
  WITH cand AS (
    -- Righe DDT eleggibili + riga d'ordine (via fulfillment) +
    -- differenza di partita dal contatore.
    SELECT
      d.id            AS d_id,
      d.uid           AS d_uid,
      dr.id           AS dr_id,
      COALESCE(d.billing_account_id, src.src_billing_account_id) AS ba_id,
      ba.utility_id           AS ba_utility_id,
      ba.istanza_utility_id   AS ba_istanza,
      d.data          AS d_data,
      d.numero        AS d_numero,
      d.anno          AS d_anno,
      d.serie         AS d_serie,
      d.valuta_id     AS d_valuta,
      dr.articolo_id  AS dr_articolo,
      dr.quantita     AS dr_quantita,
      dr.qta_operativa AS dr_qta_op,
      dr.uom_operativa_id AS dr_uom_op,
      dr.factor_to_base   AS dr_factor,
      dr.prezzo_unitario  AS dr_prezzo,
      a.uom_id        AS a_uom,
      a.is_composito  AS a_composito,
      src.src_ordine_uid,
      src.src_fatturazione_trigger,
      src.src_prezzo_unitario,
      src.src_valuta_id,
      src.src_ordine_riga_id,
      ct.differenza   AS partita_diff
    FROM vendite.ddt d
    JOIN config.stati_doc_ddt sdd ON sdd.id = d.stato_doc_ddt_id
    -- CINTURA solo-trasporto (DL-28): la causale dichiara se la
    -- merce che viaggia e' una vendita. Vale per entrambi i rami:
    -- descrive il viaggio, non la provenienza del documento.
    -- INNER JOIN: la causale e' obbligatoria dall'emissione (gate
    -- 20260718-04) e qui si guardano solo stati >= SPEDITO.
    JOIN config.causali_trasporto caus
      ON caus.id = d.causale_trasporto_id
     AND caus.fatturabile IS TRUE
    JOIN vendite.ddt_righe dr
      ON dr.ddt_id = d.id
     AND dr.attivo IS TRUE
    JOIN catalogo.articoli a ON a.id = dr.articolo_id
    LEFT JOIN LATERAL (
      SELECT
        o_src.billing_account_id   AS src_billing_account_id,
        o_src.fatturazione_trigger AS src_fatturazione_trigger,
        o_src.uid                  AS src_ordine_uid,
        o_src.valuta_id            AS src_valuta_id,
        or_r.prezzo_unitario       AS src_prezzo_unitario,
        or_r.id                    AS src_ordine_riga_id
      FROM vendite.ordini_righe_fulfillment ful
      JOIN vendite.ordini_righe or_r ON or_r.id = ful.ordine_riga_id
      JOIN vendite.ordini o_src      ON o_src.id = or_r.ordine_id
      WHERE ful.ddt_riga_id = dr.id
      ORDER BY ful.id LIMIT 1
    ) src ON TRUE
    -- Rank dello stato-trigger dell'ordine, per chiave naturale
    -- stabile. CONFERMATO non esiste fra gli stati DDT -> non
    -- risolve -> il ramo order-backed e' falso (§3e.3).
    LEFT JOIN config.stati_doc_ddt sdd_trg
      ON sdd_trg.codice_interno = src.src_fatturazione_trigger
    JOIN anagrafiche.billing_account ba
      ON ba.id = COALESCE(d.billing_account_id, src.src_billing_account_id)
    LEFT JOIN vendite.vw_contatore_merce ct
      ON ct.ordine_riga_id = src.src_ordine_riga_id
    WHERE COALESCE(d.billing_account_id, src.src_billing_account_id) IS NOT NULL
      AND (
        -- ORDER-BACKED: dallo stato-trigger IN POI (fix orfano §1c),
        -- ma mai su un documento morto (ANNULLATO, via is_abortito)
        -- ne' su merce tutta tornata indietro (RESO).
        (src.src_fatturazione_trigger IS NOT NULL
         AND src.src_fatturazione_trigger != 'CONFERMATO'   -- cintura XOR: NON toccare
         AND sdd_trg.ordine IS NOT NULL
         AND sdd.ordine >= sdd_trg.ordine
         AND NOT sdd.is_abortito
         AND sdd.codice_interno <> 'RESO')
        OR
        -- STANDALONE: invariato (gia' privo di RESO/ANNULLATO).
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
  ),
  dist AS (
    -- Distribuzione della differenza per riga DDT (greedy oldest-first,
    -- cappata a dr.quantita). Order-backed non composito -> differenza;
    -- standalone / composito -> dr.quantita grezza (invariato).
    SELECT c.*,
      CASE
        WHEN c.src_ordine_riga_id IS NOT NULL AND NOT COALESCE(c.a_composito, false)
          THEN GREATEST(0::numeric, LEAST(
                 c.dr_quantita,
                 COALESCE(c.partita_diff, 0)
                 - COALESCE(SUM(c.dr_quantita) OVER (
                       PARTITION BY c.src_ordine_riga_id
                       ORDER BY c.d_id, c.dr_id
                       ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), 0)
               ))
        ELSE c.dr_quantita
      END AS quantita_push
    FROM cand c
  )
  SELECT
    x.d_id,
    x.d_uid,
    x.dr_id,
    x.ba_id,
    x.ba_utility_id,
    anagrafiche.fn_get_emittente_fiscale_id(x.ba_id),
    x.d_data,
    x.d_data,
    FALSE,
    v_sorgente_tipo_id,
    x.d_uid::text,
    ('DDT:' || x.d_uid::text || ':R:' || x.dr_id::text)::varchar,
    x.dr_articolo,
    x.ba_istanza,
    x.d_data,
    x.a_uom,
    x.quantita_push,
    -- qta_operativa scalata proporzionalmente (ratio = 1 se nessuna riduzione)
    x.dr_qta_op * (x.quantita_push / NULLIF(x.dr_quantita, 0)),
    x.dr_uom_op,
    COALESCE(x.dr_factor, 1::numeric),
    date_trunc('month', x.d_data)::date,
    COALESCE(x.dr_prezzo, x.src_prezzo_unitario),
    (COALESCE(x.dr_prezzo, x.src_prezzo_unitario) IS NOT NULL),
    'FIXED'::varchar,
    'NORMALE'::varchar,
    'CONGUAGLIO'::varchar,
    COALESCE(x.d_valuta, x.src_valuta_id),
    jsonb_build_object(
      'ddt_numero',          x.d_numero,
      'ddt_anno',            x.d_anno,
      'ddt_serie',           x.d_serie,
      'ordine_sorgente_uid', x.src_ordine_uid,
      'ordine_fatturaz_trg', x.src_fatturazione_trigger,
      'tipo_commessa',       'AUTO',
      'policy_fatturazione', 'DA_DOCUMENTO'
    ),
    v_tipo_doc_fiscale_id
  FROM dist x
  WHERE x.quantita_push > 0
  ORDER BY x.d_id, x.dr_id
  LIMIT p_limit;
END
$function$

COMMENT ON FUNCTION vendite.fn_list_ddt_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer, p_ddt_id bigint)
IS 'Lista righe DDT eligible al push su commessa. rev 2026-07-18 (step 5b): esclude i DDT con causale di trasporto NON fatturabile (config.causali_trasporto.fatturabile, DL-28) — cintura su entrambi i rami, la causale descrive il viaggio della merce non la provenienza del documento; INNER JOIN perche'' la causale e'' obbligatoria dall''emissione (gate trgfn_ddt_guard_causale_emissione). rev 2026-07-18 (step 5): eleggibilita'' order-backed DALLO stato-trigger IN POI (sdd.ordine >= rank del trigger) AND NOT is_abortito AND <> RESO, cintura XOR != CONFERMATO PRESERVATA. rev 2026-07-17 (step 3): proietta come quantita la DIFFERENZA del contatore vw_contatore_merce distribuita per riga DDT (greedy, cappata a dr.quantita); qta_operativa scalata; standalone e compositi a dr.quantita grezza; filtra quantita_push > 0. rev 2026-06-28: sorgente/stato per codice_interno.';
```

---
{% include-markdown "signature-core.md" %}
