{% include-markdown "it/dbzero/vendite/manual/fn_ddt_push_diagnosi.md" %}
# ⚙️ Funzione `fn_ddt_push_diagnosi`

```sql
CREATE FUNCTION fn_ddt_push_diagnosi(p_ddt_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ddt_push_diagnosi(p_ddt_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(ddt_id bigint, riga_id bigint, motivo_rank integer, motivo text, billing_account_id bigint, ordine_riga_id bigint, segment text, quantita_push numeric)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 WITH docs AS (
          SELECT d.id,
             d.uid,
             d.stato_doc_ddt_id,
             d.causale_trasporto_id,
             d.billing_account_id,
             d.sorgente_tipo_id,
             d.sorgente_uid,
             d.sorgente_id
            FROM vendite.ddt d
           WHERE (d.id = fn_ddt_push_diagnosi.p_ddt_id)
         UNION ALL
          SELECT d.id,
             d.uid,
             d.stato_doc_ddt_id,
             d.causale_trasporto_id,
             d.billing_account_id,
             d.sorgente_tipo_id,
             d.sorgente_uid,
             d.sorgente_id
            FROM vendite.ddt d
           WHERE (fn_ddt_push_diagnosi.p_ddt_id IS NULL)
         ), pm AS MATERIALIZED (
          SELECT p.ddt_riga_id,
             p.differenza,
             p.stato
            FROM vendite.fn_partite_merce(
                 CASE
                     WHEN (fn_ddt_push_diagnosi.p_ddt_id IS NULL) THEN NULL::bigint[]
                     ELSE ARRAY[fn_ddt_push_diagnosi.p_ddt_id]
                 END, NULL::bigint[]) p(ddt_riga_id, ddt_id, ddt_uid, articolo_id, is_composito, ordine_riga_id, ordine_id, origine, fatturabile, consegnato, reso, in_riconsegna, tenuti, fatturato_merce, fatturato_da_ordine, fatturato, misurabile, differenza, stato, e_riconsegna, sospetto_duplicato_ordine, rettificato, riconsegna_quota_nuova)
         ), righe AS (
          SELECT d.id AS d_id,
             d.uid AS d_uid,
             d.stato_doc_ddt_id,
             d.causale_trasporto_id,
             d.billing_account_id AS d_ba,
             d.sorgente_tipo_id AS d_src_tipo,
             d.sorgente_uid AS d_src_uid,
             d.sorgente_id AS d_src_id,
             dr.id AS dr_id,
             dr.quantita,
             (script.fn_natura_e_merce(dr.natura_vendita_id) IS FALSE) AS e_onere
            FROM (docs d
              JOIN vendite.ddt_righe dr ON (((dr.ddt_id = d.id) AND (dr.attivo IS TRUE))))
         ), src AS MATERIALIZED (
          SELECT r.dr_id,
                 CASE
                     WHEN (s.src_ordine_riga_id IS NOT NULL) THEN s.src_fatturazione_trigger
                     WHEN r.e_onere THEN vendite.fn_ddt_trigger_ordine_testata(r.d_src_tipo, r.d_src_uid, r.d_src_id)
                     ELSE NULL::character varying
                 END AS src_fatturazione_trigger,
             s.src_ordine_riga_id
            FROM (righe r
              LEFT JOIN LATERAL ( SELECT o.fatturazione_trigger AS src_fatturazione_trigger,
                     orr.id AS src_ordine_riga_id
                    FROM ((vendite.ordini_righe_fulfillment ful
                      JOIN vendite.ordini_righe orr ON ((orr.id = ful.ordine_riga_id)))
                      JOIN vendite.ordini o ON ((o.id = orr.ordine_id)))
                   WHERE (ful.ddt_riga_id = r.dr_id)
                   ORDER BY ful.id
                  LIMIT 1) s ON (true))
         ), ba_vis AS MATERIALIZED (
          SELECT b.id
            FROM anagrafiche.billing_account b
           WHERE (b.id IN ( SELECT DISTINCT r.d_ba
                    FROM righe r
                   WHERE (r.d_ba IS NOT NULL)))
         ), cand AS (
          SELECT r.d_id,
             r.dr_id,
             ba.id AS ba_id,
             s.src_ordine_riga_id,
             sdd.codice_interno AS sdd_cod,
             sdd.ordine AS sdd_ord,
             sdd.is_abortito AS sdd_abort,
             caus.fatturabile AS caus_fatt,
             s.src_fatturazione_trigger AS trg,
             sdd_trg.ordine AS trg_ord,
             pm.ddt_riga_id AS pm_presente,
             pm.stato AS pm_stato,
             r.e_onere,
             script.fn_get_stato_push_segment(script.fn_segment_key('DDT_VENDITA'::character varying, (r.d_uid)::text, r.dr_id)) AS segment,
                 CASE
                     WHEN r.e_onere THEN r.quantita
                     ELSE GREATEST((0)::numeric, LEAST(r.quantita, COALESCE(pm.differenza, (0)::numeric)))
                 END AS qta_push
            FROM ((((((righe r
              JOIN config.stati_doc_ddt sdd ON ((sdd.id = r.stato_doc_ddt_id)))
              LEFT JOIN src s ON ((s.dr_id = r.dr_id)))
              LEFT JOIN config.causali_trasporto caus ON ((caus.id = r.causale_trasporto_id)))
              LEFT JOIN pm ON ((pm.ddt_riga_id = r.dr_id)))
              LEFT JOIN ba_vis ba ON ((ba.id = r.d_ba)))
              LEFT JOIN config.stati_doc_ddt sdd_trg ON (((sdd_trg.codice_interno)::text = (s.src_fatturazione_trigger)::text)))
         ), diag AS (
          SELECT c.d_id,
             c.dr_id,
             c.ba_id,
             c.src_ordine_riga_id,
             c.sdd_cod,
             c.sdd_ord,
             c.sdd_abort,
             c.caus_fatt,
             c.trg,
             c.trg_ord,
             c.pm_presente,
             c.pm_stato,
             c.e_onere,
             c.segment,
             c.qta_push,
             ( SELECT r.rank
                    FROM ( VALUES (1,c.sdd_abort), (1,((c.sdd_cod)::text = 'RESO'::text)), (2,(c.caus_fatt IS NOT TRUE)), (3,(c.ba_id IS NULL)), (4,(c.segment <> 'LIBERA'::text)), (5,((c.trg IS NOT NULL) AND ((c.trg)::text <> 'CONFERMATO'::text) AND ((c.trg_ord IS NULL) OR (c.sdd_ord < c.trg_ord)))), (5,((c.trg IS NULL) AND ((c.sdd_cod)::text <> ALL (ARRAY[('SPEDITO'::character varying)::text, ('CONSEGNATO'::character varying)::text])))), (6,((c.trg)::text = 'CONFERMATO'::text)), (7,((NOT c.e_onere) AND ((c.pm_stato)::text = 'RICONSEGNA'::text))), (8,((NOT c.e_onere) AND ((c.pm_stato)::text = 'NON_FATTURABILE'::text))), (9,((NOT c.e_onere) AND ((c.pm_stato)::text = 'NON_MISURABILE'::text))), (10,((NOT c.e_onere) AND (c.pm_presente IS NULL))), (11,((NOT c.e_onere) AND (c.qta_push <= (0)::numeric)))) r(rank, hit)
                   WHERE r.hit
                   ORDER BY r.rank
                  LIMIT 1) AS mrank
            FROM cand c
         )
  SELECT diag.d_id,
     diag.dr_id,
     diag.mrank,
         CASE diag.mrank
             WHEN 1 THEN
             CASE
                 WHEN ((diag.sdd_cod)::text = 'RESO'::text) THEN 'DDT_RESO'::text
                 ELSE 'DDT_ANNULLATO'::text
             END
             WHEN 2 THEN 'DDT_SOLO_TRASPORTO'::text
             WHEN 3 THEN 'DDT_SENZA_BA'::text
             WHEN 4 THEN 'DDT_ROUTED'::text
             WHEN 5 THEN 'DDT_MERCE_IN_VIAGGIO'::text
             WHEN 6 THEN 'DDT_FATTURA_DA_ORDINE'::text
             WHEN 7 THEN 'DDT_RICONSEGNA'::text
             WHEN 8 THEN 'DDT_NON_FATTURABILE'::text
             WHEN 9 THEN 'DDT_NON_MISURABILE'::text
             WHEN 10 THEN 'DDT_SENZA_PARTITA'::text
             WHEN 11 THEN 'DDT_CONTATORE'::text
             ELSE NULL::text
         END AS "case",
     diag.ba_id,
     diag.src_ordine_riga_id,
     diag.segment,
     diag.qta_push
    FROM diag;
END

COMMENT ON FUNCTION vendite.fn_ddt_push_diagnosi(p_ddt_id bigint)
IS 'La fonte unica dell''eleggibilita'' al push a commessa: per ogni riga ATTIVA di bolla, il motivo di esclusione (NULL = eleggibile) e i fatti per chi agisce: billing_account_id (della testata; NULL se manca o se invisibile a chi legge), ordine_riga_id (la riga d''ordine sorgente, primo fulfillment per id), segment (LIBERA, ALLOCATA, EMESSA da script.fn_get_stato_push_segment), quantita_push (GREATEST(0, LEAST(quantita, differenza della partita))). p_ddt_id NULL = tutte le righe. vendite.fn_list_ddt_da_pushare deriva da qui, script.fn_available_actions_ddt la legge una volta: un predicato di eleggibilita'' nuovo si aggiunge qui come rank. motivo_rank = precedenza: 1 ANNULLATO/RESO, 2 SOLO_TRASPORTO (causale non fatturabile o assente), 3 SENZA_BA, 4 ROUTED, 5 MERCE_IN_VIAGGIO, 6 FATTURA_DA_ORDINE, 7 RICONSEGNA, 8 NON_FATTURABILE, 9 NON_MISURABILE, 10 SENZA_PARTITA, 11 CONTATORE. La riga-onere (script.fn_natura_e_merce false sulla natura congelata) non e'' merce: le rank della partita (7-11) non la guardano e la dose e'' la sua quantita''; le rank 1-6 valgono come per la merce, e per l''onere senza legame il trigger dell''ordine si legge da vendite.fn_ddt_trigger_ordine_testata con la sorgente intera della bolla (tipo, uid, id). La chiave della riga la compone script.fn_segment_key. Il billing account e'' uno, quello della testata. Tutto si legge per seme, e le CTE MATERIALIZED sono la forma: la partita da vendite.fn_partite_merce col seme della bolla (pm), i billing account visibili seminati dalle chiavi in gioco (ba_vis, INVOKER: un billing account che la policy non mostra lascia la riga SENZA_BA), la riga d''ordine sorgente (src). Il documento chiesto e'' un seme a due rami in UNION ALL. BEGIN ATOMIC.';
```

</div>

---
{% include-markdown "signature-core.md" %}
