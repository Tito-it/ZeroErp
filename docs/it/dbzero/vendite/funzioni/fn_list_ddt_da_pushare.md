{% include-markdown "it/dbzero/vendite/manual/fn_list_ddt_da_pushare.md" %}
# ⚙️ Funzione `fn_list_ddt_da_pushare`

```sql
CREATE FUNCTION fn_list_ddt_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer, p_ddt_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_list_ddt_da_pushare(p_competenza_mese date DEFAULT NULL::date, p_billing_account_id bigint DEFAULT NULL::bigint, p_limit integer DEFAULT NULL::integer, p_ddt_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(ddt_id bigint, ddt_uid uuid, riga_id bigint, billing_account_id bigint, utility_id integer, emittente_soggetto_ruolo_id bigint, competenza_dal date, competenza_al date, fatturazione_immediata boolean, sorgente_tipo_id bigint, sorgente_chiave text, segment_key character varying, articolo_id uuid, istanza_utility_id bigint, data_attivita date, uom_id bigint, quantita numeric, qta_operativa numeric, uom_operativa_id bigint, factor_to_base numeric, competenza_mese date, prezzo_snapshot numeric, prezzo_bloccato boolean, pricing_mode character varying, tipo_movimento character varying, valuta_id integer, meta jsonb, tipo_doc_fiscale_id bigint, termine_pagamento_id bigint, modalita_pagamento_id integer, causale_onere_id bigint, origine_prezzo character varying, listino_versione_id bigint, listino_riga_id bigint, prezzo_base_snapshot numeric, tipo_variazione_applicata character varying, valore_variazione_applicata numeric, promo_id bigint, prezzo_contratto_id bigint, categoria_cliente_id_snapshot smallint, classe_utenza_id_snapshot integer)
 LANGUAGE plpgsql
 SET plan_cache_mode TO 'force_generic_plan'
AS $function$
-- rev 2026-11-03 (20261103-40, brief-db-addebito-trasporto-ordine §8.1, K-1):
--   la riga-onere (script.fn_natura_e_merce = false sulla natura congelata)
--   esce tipo_movimento ONERE con la causale dell'articolo, nella colonna
--   nuova causale_onere_id (DROP + CREATE). Sorgente: la bolla. Chi e'
--   eleggibile e la dose li dice ancora la diagnosi (20261103-39).
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
      -- La provenienza del prezzo che esce (F-4): della riga del DDT se ha
      -- il prezzo, altrimenti della riga d'ordine, come il COALESCE sotto.
      CASE WHEN dr.prezzo_unitario IS NOT NULL THEN dr.origine_prezzo ELSE or_r.origine_prezzo END AS pv_origine,
      CASE WHEN dr.prezzo_unitario IS NOT NULL THEN dr.listino_versione_id ELSE or_r.listino_versione_id END AS pv_versione,
      CASE WHEN dr.prezzo_unitario IS NOT NULL THEN dr.listino_riga_id ELSE or_r.listino_riga_id END AS pv_riga,
      CASE WHEN dr.prezzo_unitario IS NOT NULL THEN dr.prezzo_resolver_context ELSE or_r.prezzo_resolver_context END AS pv_contesto,
      a.uom_id        AS a_uom,
      -- rev 2026-11-03: proiezione, non eleggibilita' (quella e' della
      -- diagnosi). IS FALSE: una natura sconosciuta resta merce.
      (script.fn_natura_e_merce(dr.natura_vendita_id) IS FALSE) AS dr_e_onere,
      a.causale_onere_id AS a_causale_onere,
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
    -- rev 2026-11-03 (K-1): la riga-onere va in commessa come ONERE, con la
    -- causale dell'articolo e la bolla come sorgente.
    CASE WHEN x.dr_e_onere THEN 'ONERE' ELSE 'NORMALE' END::varchar,
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
    NULL::integer,
    -- La causale dall'articolo solo qui, dove serve il valore (decisione 2
    -- di Tid). ONERE <=> causale: lo pretende la madre
    -- vendite.fn_upsert_commessa_attivita; un articolo-onere rimasto senza
    -- causale esce ONERE senza causale e la madre lo rifiuta (rumoroso).
    CASE WHEN x.dr_e_onere THEN x.a_causale_onere END,
    pv.origine_prezzo,
    pv.listino_versione_id,
    pv.listino_riga_id,
    pv.prezzo_base_snapshot,
    pv.tipo_variazione_applicata,
    pv.valore_variazione_applicata,
    pv.promo_id,
    pv.prezzo_contratto_id,
    pv.categoria_cliente_id_snapshot,
    pv.classe_utenza_id_snapshot
  FROM cand x
  -- La provenienza del prezzo della riga, nelle colonne della commessa (R-3).
  CROSS JOIN LATERAL vendite.fn_provenienza_prezzo_esplosa(
    x.pv_origine, x.pv_versione, x.pv_riga, x.pv_contesto) pv
  ORDER BY x.d_id, x.dr_id
  LIMIT p_limit;
END
$function$

COMMENT ON FUNCTION vendite.fn_list_ddt_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer, p_ddt_id bigint)
IS 'Le righe delle bolle di vendita da mandare in commessa. L''eleggibilita'' e la dose stanno in un posto solo, vendite.fn_ddt_push_diagnosi: il lister ne prende le righe senza motivo e aggiunge i filtri di chiamata (competenza, billing account, limite) e la proiezione. Dalla diagnosi vengono il billing account, la riga d''ordine sorgente e la quantita'' da mandare (la differenza della partita di merce di vendite.fn_partite_merce; per un onere, la quantita'' della riga); una partita non misurabile non parte. Un predicato nuovo si aggiunge alla diagnosi, non qui. p_ddt_id: una bolla sola, letta come seme della partita (NULL = tutte; <= 0 solleva E_PUSH_SORGENTE_ID_INVALIDO); la sorgente DDT_VENDITA assente dal catalogo solleva E_CODICE. Ordine per bolla e riga, p_limit come tetto. La chiave del documento esce in sorgente_chiave, l''uid della bolla in testo, come la riceve la madre vendite.fn_upsert_commessa_attivita (p_sorgente_chiave) e come la legge la chiave sorgente_chiave del batch vendite.fn_batch_upsert_commessa_attivita; la chiave del push DDT_VENDITA:<uid>:R:<riga> la compone script.fn_segment_key. Prezzo e valuta sono quelli della riga o, se mancano, della riga d''ordine sorgente; prezzo_bloccato e'' vero quando un prezzo c''e''. fatturazione_immediata e'' quella della bolla. Una riga-onere (script.fn_natura_e_merce falso sulla natura della riga) esce con tipo_movimento ONERE e la causale dell''articolo in causale_onere_id; la merce esce NORMALE, con causale_onere_id NULL. termine_pagamento_id e modalita_pagamento_id sono NULL. Gira col piano generico (plan_cache_mode). Il backend legge le colonne per nome. Restituisce anche la provenienza del prezzo, nelle colonne della riga di commessa (origine_prezzo, listino_versione_id, listino_riga_id, prezzo_base_snapshot, tipo_variazione_applicata, valore_variazione_applicata, promo_id, prezzo_contratto_id, categoria_cliente_id_snapshot, classe_utenza_id_snapshot): quella della riga del DDT se ha il prezzo, altrimenti quella della riga d''ordine da cui il prezzo viene (vendite.fn_provenienza_prezzo_esplosa).';
```

</div>

---
{% include-markdown "signature-core.md" %}
