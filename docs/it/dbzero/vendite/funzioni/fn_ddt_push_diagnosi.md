{% include-markdown "it/dbzero/vendite/manual/fn_ddt_push_diagnosi.md" %}
# ⚙️ Funzione `fn_ddt_push_diagnosi`

```sql
CREATE FUNCTION fn_ddt_push_diagnosi(p_ddt_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ddt_push_diagnosi(p_ddt_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(ddt_id bigint, riga_id bigint, motivo_rank integer, motivo text)
 LANGUAGE sql
 STABLE
AS $function$
  -- Scopo: per ogni riga DDT, IL motivo per cui non e' inviabile
  --   a commessa (NULL = eleggibile). Fonte unica dei predicati
  --   del lister vendite.fn_list_ddt_da_pushare (equivalenza
  --   blindata a pgTAP). p_ddt_id NULL = tutte le righe.
  -- rev 2026-08-18: riallineata alla PARTITA (§23.2 del brief
  --   partita generalizzata). Prima leggeva vw_contatore_merce
  --   per riga d'ordine e rifaceva la ridistribuzione greedy che
  --   S5 aveva tolto dal lister: erano due implementazioni della
  --   stessa regola.
  -- rev 2026-09-21 (D14, quarta leva): la partita si legge da
  --   vendite.fn_partite_merce col DDT come seme (la chiusura del
  --   documento); p_ddt_id NULL = tutte. Stessi numeri del lister,
  --   per costruzione: e' la stessa funzione.
  WITH cand AS (
    -- ⚠️ Gli INNER JOIN del lister diventano LEFT JOIN qui: la
    -- diagnosi deve SPIEGARE l'esclusione, non ripeterla. Ogni
    -- join che il lister usa per escludere ha sotto una rank.
    SELECT
      d.id   AS d_id,
      dr.id  AS dr_id,
      COALESCE(d.billing_account_id, src.src_billing_account_id) AS ba_id,
      sdd.codice_interno AS sdd_cod,
      sdd.ordine         AS sdd_ord,
      sdd.is_abortito    AS sdd_abort,
      caus.fatturabile   AS caus_fatt,
      dr.quantita        AS dr_quantita,
      src.src_fatturazione_trigger AS trg,
      sdd_trg.ordine     AS trg_ord,
      -- ⭐ LA PARTITA, per riga di DDT. `stato` e' gia' la
      -- decomposizione di «differenza IS NULL» nelle sue tre
      -- cause: si legge, non si ri-deriva.
      pm.ddt_riga_id     AS pm_presente,
      pm.stato           AS pm_stato,
      pm.differenza      AS pm_diff,
      script.fn_get_stato_push_segment(
        'DDT:'||d.uid::text||':R:'||dr.id::text) AS segment
    FROM vendite.ddt d
    JOIN config.stati_doc_ddt sdd ON sdd.id = d.stato_doc_ddt_id
    JOIN vendite.ddt_righe dr ON dr.ddt_id = d.id AND dr.attivo IS TRUE
    LEFT JOIN config.causali_trasporto caus ON caus.id = d.causale_trasporto_id
    LEFT JOIN vendite.fn_partite_merce(
           CASE WHEN p_ddt_id IS NULL THEN NULL::bigint[] ELSE ARRAY[p_ddt_id] END,
           NULL::bigint[]) pm ON pm.ddt_riga_id = dr.id
    LEFT JOIN LATERAL (
      SELECT o.billing_account_id   AS src_billing_account_id,
             o.fatturazione_trigger AS src_fatturazione_trigger
      FROM vendite.ordini_righe_fulfillment ful
      JOIN vendite.ordini_righe orr ON orr.id = ful.ordine_riga_id
      JOIN vendite.ordini o        ON o.id = orr.ordine_id
      WHERE ful.ddt_riga_id = dr.id ORDER BY ful.id LIMIT 1
    ) src ON TRUE
    LEFT JOIN config.stati_doc_ddt sdd_trg
      ON sdd_trg.codice_interno = src.src_fatturazione_trigger
    WHERE (p_ddt_id IS NULL OR d.id = p_ddt_id)
  ),
  diag AS (
    -- IL motivo, per precedenza. Le rank 7..10 stanno PRIMA di
    -- DDT_CONTATORE apposta: una partita senza conto ha
    -- differenza NULL, quindi quantita 0 — e il contatore
    -- scatterebbe per primo mascherando la ragione vera.
    SELECT c.*,
      (SELECT r.rank FROM (VALUES
        (1,  c.sdd_abort),                                  -- ANNULLATO
        (1,  c.sdd_cod = 'RESO'),                           -- RESO
        -- ⚠️ `IS NOT TRUE` e non `IS FALSE`: il lister fa un
        -- INNER JOIN con `fatturabile IS TRUE`, quindi la
        -- causale ASSENTE esclude quanto quella non fatturabile.
        (2,  c.caus_fatt IS NOT TRUE),
        (3,  c.ba_id IS NULL),
        (4,  c.segment <> 'LIBERA'),
        (5,  c.trg IS NOT NULL AND c.trg <> 'CONFERMATO'
             AND (c.trg_ord IS NULL OR c.sdd_ord < c.trg_ord)),
        (5,  c.trg IS NULL
             AND c.sdd_cod NOT IN ('SPEDITO','CONSEGNATO')),
        (6,  c.trg = 'CONFERMATO'),
        -- 🆕 I tre motivi che il lister riassume in
        -- `pm.differenza IS NOT NULL`, letti dalla partita.
        (7,  c.pm_stato = 'RICONSEGNA'),
        (8,  c.pm_stato = 'NON_FATTURABILE'),
        (9,  c.pm_stato = 'NON_MISURABILE'),
        -- 🆕 Fallback: nessuna partita affatto (DDT sotto
        -- EMESSO, decisione D1). Esiste perche' una riga esclusa
        -- dal lister NON deve mai uscire di qui con motivo NULL:
        -- «eleggibile» e' la bugia peggiore per questa funzione.
        (10, c.pm_presente IS NULL),
        -- C'e' un conto, ed e' <= 0: tutto gia' fatturato.
        (11, GREATEST(0::numeric,
               LEAST(c.dr_quantita, COALESCE(c.pm_diff, 0))) <= 0)
      ) AS r(rank, hit) WHERE r.hit ORDER BY r.rank LIMIT 1) AS mrank
    FROM cand c
  )
  SELECT d_id, dr_id, mrank,
         CASE mrank
           WHEN 1  THEN CASE WHEN sdd_cod = 'RESO' THEN 'DDT_RESO' ELSE 'DDT_ANNULLATO' END
           WHEN 2  THEN 'DDT_SOLO_TRASPORTO'
           WHEN 3  THEN 'DDT_SENZA_BA'
           WHEN 4  THEN 'DDT_ROUTED'
           WHEN 5  THEN 'DDT_MERCE_IN_VIAGGIO'
           WHEN 6  THEN 'DDT_FATTURA_DA_ORDINE'
           WHEN 7  THEN 'DDT_RICONSEGNA'
           WHEN 8  THEN 'DDT_NON_FATTURABILE'
           WHEN 9  THEN 'DDT_NON_MISURABILE'
           WHEN 10 THEN 'DDT_SENZA_PARTITA'
           WHEN 11 THEN 'DDT_CONTATORE'
         END
    FROM diag
$function$

COMMENT ON FUNCTION vendite.fn_ddt_push_diagnosi(p_ddt_id bigint)
IS 'rev 2026-09-21 (D14, quarta leva): la partita si legge da vendite.fn_partite_merce con il DDT chiesto come SEME (la chiusura del documento); p_ddt_id NULL = tutte. Stessa sorgente del lister, quindi stessi numeri per costruzione. Fonte unica: per riga DDT, IL motivo di esclusione dalla push a commessa (NULL = eleggibile). Riproduce i predicati di vendite.fn_list_ddt_da_pushare in un unico posto (equivalenza righe-NULL == output lister, blindata da pgTAP). motivo_rank = precedenza: 1 ANNULLATO/RESO, 2 SOLO_TRASPORTO (causale non fatturabile O ASSENTE — il lister fa un INNER JOIN con fatturabile IS TRUE), 3 SENZA_BA, 4 ROUTED, 5 MERCE_IN_VIAGGIO, 6 FATTURA_DA_ORDINE, 7 RICONSEGNA, 8 NON_FATTURABILE, 9 NON_MISURABILE, 10 SENZA_PARTITA, 11 CONTATORE. La capability script.fn_available_actions_ddt consuma il min(rank) per il ramo reason e mappa per STRINGA, non per numero: rinumerare non la rompe, e il suo CASE ha un ELSE che fa cadere i motivi nuovi nel generico. rev 2026-08-18 (§23.2 brief-design-partita-merce-generalizzata): RIALLINEATA ALLA PARTITA. Prima leggeva vw_contatore_merce per riga d''ORDINE e rifaceva la ridistribuzione greedy + il caso speciale sui compositi che S5 (20260817-10) aveva tolto dal lister: erano DUE implementazioni della regola che dosa la fatturazione, e questa si dichiarava fonte unica di entrambe. I tre motivi 7/8/9 non ri-derivano niente: si leggono da vw_partite_merce.stato, che E'' gia'' la decomposizione di «differenza IS NULL» (e_riconsegna | NOT conta_fatturazione | NOT misurabile). Il 10 e'' un fallback deliberato: una riga esclusa dal lister non deve MAI uscire con motivo NULL. Brief: brief-db-ddt-reason-push-catch-all §3 (Decisione A) + brief-design-partita-merce-generalizzata §23.2.';
```

---
{% include-markdown "signature-core.md" %}
