{% include-markdown "it/dbzero/vendite/manual/fn_list_ddt_da_pushare.md" %}
# ⚙️ Funzione `fn_list_ddt_da_pushare`

```sql
CREATE FUNCTION fn_list_ddt_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer, p_ddt_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_list_ddt_da_pushare(p_competenza_mese date DEFAULT NULL::date, p_billing_account_id bigint DEFAULT NULL::bigint, p_limit integer DEFAULT NULL::integer, p_ddt_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(ddt_id bigint, ddt_uid uuid, riga_id bigint, billing_account_id bigint, utility_id integer, emittente_soggetto_ruolo_id bigint, competenza_dal date, competenza_al date, fatturazione_immediata boolean, sorgente_tipo_id bigint, sorgente_uid text, segment_key character varying, articolo_id uuid, istanza_utility_id bigint, data_attivita date, uom_id bigint, quantita numeric, qta_operativa numeric, uom_operativa_id bigint, factor_to_base numeric, competenza_mese date, prezzo_snapshot numeric, prezzo_bloccato boolean, pricing_mode character varying, tipo_movimento character varying, valuta_id integer, meta jsonb, tipo_doc_fiscale_id bigint, termine_pagamento_id bigint, modalita_pagamento_id integer)
 LANGUAGE plpgsql
 SET plan_cache_mode TO 'force_generic_plan'
AS $function$
-- rev 2026-10-20 (20261020-91, brief-db-grammatica-unica-documenti, 2e G-8):
--   la chiave e' DDT_VENDITA:<uid>:R:<riga>, composta da
--   script.fn_segment_key (era DDT:...). Firma e RETURNS ancorati.
DECLARE
  v_sorgente_tipo_id    config.sorgenti.id%TYPE;
  v_tipo_doc_fiscale_id config.sorgenti.tipo_doc_fiscale_id%TYPE;
BEGIN
  -- rev 2026-06-28: sorgente/stato DDT per codice_interno (immutabile).
  -- rev 2026-07-17 (step 3): proietta la differenza del contatore.
  -- rev 2026-07-18 (step 5): eleggibilita' dallo stato-trigger IN POI.
  -- rev 2026-07-18 (step 5b): esclude le causali non fatturabili.
  -- rev 2026-07-27: fatturazione_immediata proiettata dalla COLONNA.
  -- rev 2026-08-03 (T.1): espone termine/modalita' di pagamento (NULL).
  -- rev 2026-08-17 (partita generalizzata S5): la differenza si legge
  --   dalla partita, che e' GIA' per riga di DDT.
  -- rev 2026-09-21 (D14, quarta leva): la partita col DDT come seme.
  -- ⭐ rev 2026-09-21 (D14, seconda leva, forma B2): QUESTA FUNZIONE
  --   NON DECIDE PIU' CHI E' ELEGGIBILE. Deriva da
  --   vendite.fn_ddt_push_diagnosi — la fonte unica: ogni predicato
  --   che qui era un JOIN o una riga di WHERE la' e' una rank — e
  --   aggiunge solo i filtri di chiamata e la proiezione. Le righe
  --   e le quantita' sono le stesse di prima per costruzione: la
  --   dose la calcola la diagnosi (quantita_push), una volta.
  --   ⛔ Un predicato di eleggibilita' nuovo si aggiunge alla
  --   diagnosi come rank, non qui: qui non c'e' piu' un posto.
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
    -- Le righe ELEGGIBILI le dice la diagnosi (motivo NULL). I JOIN
    -- qui sotto servono alla PROIEZIONE, non a escludere:
    --   - ddt / ddt_righe: le righe che la diagnosi ha gia' letto
    --     sotto la stessa RLS;
    --   - articoli: articolo_id e' NOT NULL e la tabella non ha RLS;
    --   - billing_account: g.billing_account_id e' NOT NULL per una
    --     riga eleggibile (rank 3) e la diagnosi lo ha gia'
    --     attraversato sotto policy;
    --   - ordini_righe / ordini: per CHIAVE, dalla riga d'ordine
    --     sorgente che la diagnosi ha scelto (primo fulfillment).
    SELECT
      d.id            AS d_id,
      d.uid           AS d_uid,
      dr.id           AS dr_id,
      g.billing_account_id AS ba_id,
      ba.utility_id           AS ba_utility_id,
      ba.istanza_utility_id   AS ba_istanza,
      d.data          AS d_data,
      d.numero        AS d_numero,
      d.anno          AS d_anno,
      d.serie         AS d_serie,
      d.valuta_id     AS d_valuta,
      -- Corsia di instradamento: trasportata fino alla SELECT finale.
      d.fatturazione_immediata AS d_fatt_immediata,
      dr.articolo_id  AS dr_articolo,
      dr.quantita     AS dr_quantita,
      dr.qta_operativa AS dr_qta_op,
      dr.uom_operativa_id AS dr_uom_op,
      dr.factor_to_base   AS dr_factor,
      dr.prezzo_unitario  AS dr_prezzo,
      a.uom_id        AS a_uom,
      o_src.uid                  AS src_ordine_uid,
      o_src.fatturazione_trigger AS src_fatturazione_trigger,
      or_r.prezzo_unitario       AS src_prezzo_unitario,
      o_src.valuta_id            AS src_valuta_id,
      -- La DOSE, dalla diagnosi: e' la stessa che la rank 11 ha
      -- giudicato > 0. Non si ricalcola.
      g.quantita_push AS quantita_push
    FROM vendite.fn_ddt_push_diagnosi(p_ddt_id) g
    JOIN vendite.ddt d        ON d.id  = g.ddt_id
    JOIN vendite.ddt_righe dr ON dr.id = g.riga_id
    JOIN catalogo.articoli a  ON a.id  = dr.articolo_id
    JOIN anagrafiche.billing_account ba ON ba.id = g.billing_account_id
    LEFT JOIN vendite.ordini_righe or_r ON or_r.id = g.ordine_riga_id
    LEFT JOIN vendite.ordini o_src      ON o_src.id = or_r.ordine_id
    WHERE g.motivo IS NULL
      -- I filtri DI CHIAMATA: non decidono l'eleggibilita', scelgono
      -- una fetta delle righe eleggibili (lista push per mese/BA).
      AND (p_competenza_mese IS NULL OR date_trunc('month', d.data)::date = p_competenza_mese)
      AND (p_billing_account_id IS NULL OR g.billing_account_id = p_billing_account_id)
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
    -- Corsia di instradamento: valore reale del DDT.
    x.d_fatt_immediata,
    v_sorgente_tipo_id,
    x.d_uid::text,
    script.fn_segment_key('DDT_VENDITA', x.d_uid::text, x.dr_id),
    x.dr_articolo,
    x.ba_istanza,
    x.d_data,
    x.a_uom,
    -- La quantita' da fatturare E' la dose della diagnosi.
    x.quantita_push,
    -- qta_operativa scalata proporzionalmente (ratio = 1 se nessuna riduzione)
    x.dr_qta_op * (x.quantita_push / NULLIF(x.dr_quantita, 0)),
    x.dr_uom_op,
    COALESCE(x.dr_factor, 1::numeric),
    date_trunc('month', x.d_data)::date,
    COALESCE(x.dr_prezzo, x.src_prezzo_unitario),
    -- prezzo_bloccato: dipende dal PREZZO della riga,
    -- INDIPENDENTE dal flag di corsia.
    (COALESCE(x.dr_prezzo, x.src_prezzo_unitario) IS NOT NULL),
    'FIXED'::varchar,
    'NORMALE'::varchar,
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
    v_tipo_doc_fiscale_id,
    NULL::bigint,
    NULL::integer
  FROM cand x
  ORDER BY x.d_id, x.dr_id
  LIMIT p_limit;
END
$function$

COMMENT ON FUNCTION vendite.fn_list_ddt_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer, p_ddt_id bigint)
IS 'rev 2026-09-21 (D14, seconda leva, forma B2): il lister DERIVA da vendite.fn_ddt_push_diagnosi — FROM fn_ddt_push_diagnosi(p_ddt_id) WHERE motivo IS NULL — e aggiunge solo i filtri di chiamata (competenza, BA, limit) e la proiezione dei 31 campi; BA, riga d''ordine sorgente e DOSE (quantita_push) li riceve dalla diagnosi. L''eleggibilita'' sta scritta in UN posto: un predicato nuovo si aggiunge alla diagnosi come rank, non qui. Contratto verso la pipeline invariato, stesse righe e stesse quantita'' per costruzione. rev 2026-09-21 (D14, quarta leva): la partita si legge da vendite.fn_partite_merce con il DDT chiesto come SEME (la chiusura del documento, non le partite di tutti); p_ddt_id NULL (lista push, cockpit) = tutte. Lista righe DDT eligible al push su commessa. rev 2026-08-17 (partita generalizzata S5): la quantita'' da fatturare e'' la DIFFERENZA della partita di merce, gia'' per riga di DDT — spariscono la ridistribuzione greedy della differenza d''ordine e il caso speciale standalone/compositi. ⚠️ Una partita NON MISURABILE non viene spinta (rank 9 della diagnosi). ⚠️ Nota per la nota di credito: quando una RETTIFICA abbassera'' il fatturato, la differenza tornera'' positiva e solo script.fn_get_stato_push_segment = LIBERA (rank 4) impedira'' la ri-spinta. rev 2026-07-18 (step 5b): esclude i DDT con causale di trasporto NON fatturabile (DL-28). rev 2026-07-18 (step 5): eleggibilita'' order-backed DALLO stato-trigger IN POI, cintura XOR != CONFERMATO PRESERVATA. rev 2026-06-28: sorgente/stato per codice_interno. rev 2026-07-19: esclusione su ALLOCAZIONE via fn_get_stato_push_segment. rev 2026-07-27: fatturazione_immediata dalla colonna. Espone termine_pagamento_id e modalita_pagamento_id a NULL (rev 2026-08-03, T.1). rev 2026-10-13 (20261013-21): tipo_consumo RITIRATO in tutta la catena del push (madre, batch, cinque lister, builder pgTAP). Non aveva un lettore, e il vocabolario della madre (ACCONTO/CONGUAGLIO/STORNO) non lo produceva nessuna sorgente con un significato: preventivi, ordini e DDT scrivevano la costante CONGUAGLIO, contratti (l''erogazione della riga) e consumi (CONSUMO) un valore che la madre rifiutava, quindi il loro push falliva sempre (E_PARAMETRO_INVALIDO). L''erogazione resta dove gia'' stava, in meta.tipo_erogazione. Decisione A di Tid, 2026-10-13. Colonna tipo_consumo tolta dal RETURNS TABLE (DROP + CREATE). Rev 2026-10-20 (20261020-91, brief-db-grammatica-unica-documenti 2e, G-8): la chiave e'' DDT_VENDITA:<uid>:R:<riga>, composta da script.fn_segment_key (era DDT:...).';
```

</div>

---
{% include-markdown "signature-core.md" %}
