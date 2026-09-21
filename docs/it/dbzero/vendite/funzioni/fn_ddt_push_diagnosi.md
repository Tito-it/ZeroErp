{% include-markdown "it/dbzero/vendite/manual/fn_ddt_push_diagnosi.md" %}
# ⚙️ Funzione `fn_ddt_push_diagnosi`

```sql
CREATE FUNCTION fn_ddt_push_diagnosi(p_ddt_id bigint)
```

**Definizione completa:**

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
             d.billing_account_id
            FROM vendite.ddt d
           WHERE (d.id = fn_ddt_push_diagnosi.p_ddt_id)
         UNION ALL
          SELECT d.id,
             d.uid,
             d.stato_doc_ddt_id,
             d.causale_trasporto_id,
             d.billing_account_id
            FROM vendite.ddt d
           WHERE (fn_ddt_push_diagnosi.p_ddt_id IS NULL)
         ), cand AS (
          SELECT d.id AS d_id,
             dr.id AS dr_id,
             ba.id AS ba_id,
             src.src_ordine_riga_id,
             sdd.codice_interno AS sdd_cod,
             sdd.ordine AS sdd_ord,
             sdd.is_abortito AS sdd_abort,
             caus.fatturabile AS caus_fatt,
             src.src_fatturazione_trigger AS trg,
             sdd_trg.ordine AS trg_ord,
             pm.ddt_riga_id AS pm_presente,
             pm.stato AS pm_stato,
             script.fn_get_stato_push_segment((((('DDT:'::text || (d.uid)::text) || ':R:'::text) || (dr.id)::text))::character varying) AS segment,
             GREATEST((0)::numeric, LEAST(dr.quantita, COALESCE(pm.differenza, (0)::numeric))) AS qta_push
            FROM (((((((docs d
              JOIN config.stati_doc_ddt sdd ON ((sdd.id = d.stato_doc_ddt_id)))
              JOIN vendite.ddt_righe dr ON (((dr.ddt_id = d.id) AND (dr.attivo IS TRUE))))
              LEFT JOIN config.causali_trasporto caus ON ((caus.id = d.causale_trasporto_id)))
              LEFT JOIN vendite.fn_partite_merce(
                 CASE
                     WHEN (fn_ddt_push_diagnosi.p_ddt_id IS NULL) THEN NULL::bigint[]
                     ELSE ARRAY[fn_ddt_push_diagnosi.p_ddt_id]
                 END, NULL::bigint[]) pm(ddt_riga_id, ddt_id, ddt_uid, articolo_id, is_composito, ordine_riga_id, ordine_id, origine, fatturabile, consegnato, reso, in_riconsegna, tenuti, fatturato_merce, fatturato_da_ordine, fatturato, misurabile, differenza, stato, e_riconsegna, sospetto_duplicato_ordine, rettificato, riconsegna_quota_nuova) ON ((pm.ddt_riga_id = dr.id)))
              LEFT JOIN LATERAL ( SELECT o.billing_account_id AS src_billing_account_id,
                     o.fatturazione_trigger AS src_fatturazione_trigger,
                     orr.id AS src_ordine_riga_id
                    FROM ((vendite.ordini_righe_fulfillment ful
                      JOIN vendite.ordini_righe orr ON ((orr.id = ful.ordine_riga_id)))
                      JOIN vendite.ordini o ON ((o.id = orr.ordine_id)))
                   WHERE (ful.ddt_riga_id = dr.id)
                   ORDER BY ful.id
                  LIMIT 1) src ON (true))
              LEFT JOIN anagrafiche.billing_account ba ON ((ba.id = COALESCE(d.billing_account_id, src.src_billing_account_id))))
              LEFT JOIN config.stati_doc_ddt sdd_trg ON (((sdd_trg.codice_interno)::text = (src.src_fatturazione_trigger)::text)))
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
             c.segment,
             c.qta_push,
             ( SELECT r.rank
                    FROM ( VALUES (1,c.sdd_abort), (1,((c.sdd_cod)::text = 'RESO'::text)), (2,(c.caus_fatt IS NOT TRUE)), (3,(c.ba_id IS NULL)), (4,(c.segment <> 'LIBERA'::text)), (5,((c.trg IS NOT NULL) AND ((c.trg)::text <> 'CONFERMATO'::text) AND ((c.trg_ord IS NULL) OR (c.sdd_ord < c.trg_ord)))), (5,((c.trg IS NULL) AND ((c.sdd_cod)::text <> ALL ((ARRAY['SPEDITO'::character varying, 'CONSEGNATO'::character varying])::text[])))), (6,((c.trg)::text = 'CONFERMATO'::text)), (7,((c.pm_stato)::text = 'RICONSEGNA'::text)), (8,((c.pm_stato)::text = 'NON_FATTURABILE'::text)), (9,((c.pm_stato)::text = 'NON_MISURABILE'::text)), (10,(c.pm_presente IS NULL)), (11,(c.qta_push <= (0)::numeric))) r(rank, hit)
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
IS 'FONTE UNICA dell''eleggibilita'' al push a commessa (rev 2026-09-21, D14 seconda leva, forma B2): per ogni riga ATTIVA di DDT, IL motivo di esclusione (NULL = eleggibile) e i fatti per chi agisce — billing_account_id (testata o ordine sorgente, letto attraverso anagrafiche.billing_account: NULL anche se invisibile a chi legge), ordine_riga_id (la riga d''ordine sorgente: primo fulfillment per id), segment (LIBERA/ALLOCATA/EMESSA da script.fn_get_stato_push_segment), quantita_push (la dose: GREATEST(0, LEAST(quantita, differenza della partita))). p_ddt_id NULL = tutte le righe. vendite.fn_list_ddt_da_pushare DERIVA da qui (FROM fn_ddt_push_diagnosi WHERE motivo IS NULL + filtri di chiamata e proiezione) e script.fn_available_actions_ddt la legge UNA volta: flag = esiste motivo NULL; poi ALLOCATA -> DDT_GIA_INVIATO, EMESSA -> DDT_GIA_FATTURATO; poi min(rank). ⛔ Un predicato di eleggibilita'' nuovo si aggiunge QUI come rank: nel lister non c''e'' piu'' un posto dove metterlo. motivo_rank = precedenza: 1 ANNULLATO/RESO, 2 SOLO_TRASPORTO (causale non fatturabile O assente), 3 SENZA_BA, 4 ROUTED, 5 MERCE_IN_VIAGGIO, 6 FATTURA_DA_ORDINE, 7 RICONSEGNA, 8 NON_FATTURABILE, 9 NON_MISURABILE, 10 SENZA_PARTITA, 11 CONTATORE. La capability mappa per STRINGA, non per numero, e il suo CASE ha un ELSE che fa cadere i motivi nuovi nel generico. BEGIN ATOMIC: le dipendenze (fn_partite_merce, fn_get_stato_push_segment, tabelle) sono in pg_depend. Il documento chiesto e'' un seme a due rami in UNION ALL, mai `p IS NULL OR`. La partita si legge da vendite.fn_partite_merce col DDT come seme (D14 quarta leva, 2026-09-21); i motivi 7/8/9 si leggono da `stato` (rev 2026-08-18, §23.2 brief-design-partita-merce-generalizzata). Brief: brief-db-partita-merce-per-documento §10; brief-db-ddt-reason-push-catch-all §3 (Decisione A).';
```

---
{% include-markdown "signature-core.md" %}
