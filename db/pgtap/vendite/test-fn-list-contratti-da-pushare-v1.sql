-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2e/L2c-1): le chiavi del push col codice della sorgente, composte da script.fn_segment_key dove la forma lo permette (le forme su piu' righe col prefisso lungo); corsia e codice del registro coi codici lunghi.
-- rev 2026-10-26 (brief-modello-documento-vendita §11): il contratto del test 3 si attiva con dbops.fn_pgtap_porta_a_stato, non piu' con l'UPDATE diretto dello stato che la porta del contratto ora rifiuta.
-- pgTAP test per Zero ERP
-- Test: vendite.fn_list_contratti_da_pushare
-- ------------------------------------------------------------
-- Indice test (1..8):
-- 1) fn_list_contratti_da_pushare presente
-- 2) Riferimenti minimi disponibili
-- 3) Contratto ATTIVO in validita restituito
-- 4) Segment key include competenza_mese (CONTR:<uid>:R:<id>:M:<YYYY-MM>)
-- 5) meta.tipo_erogazione = l'erogazione della riga (UNA_TANTUM), senza ripiego
-- 6) prezzo_bloccato = TRUE quando prezzo_unitario presente
-- 7) Contratto non ATTIVO escluso
-- 8) Filtro p_billing_account_id rispettato
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(8);

-- ============================================================
-- 0) Funzione presente
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_list_contratti_da_pushare'
  ),
  'fn_list_contratti_da_pushare presente'
);

-- ============================================================
-- 0b) Riferimenti minimi
-- ============================================================
-- 🔴 FIXTURE COSTRUITA, 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
--   Prima leggeva dal database il primo billing account e l'ultimo articolo:
--   su un DB ricostruito da zero (CI) non c'e' nessun BA, e il file finiva in
--   ERRORE_FIXTURE (baseline-rossi-ci). Ora cliente e articolo nascono qui dai
--   builder; dal DB si leggono solo gli stati e la sorgente, che sono seed.
--   Con il contesto aperto il builder lega il BA all'azienda di chi agisce.
CREATE TEMP TABLE tmp_cli_contr AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('pgTAP lister contratti');

CREATE TEMP TABLE tmp_refs_contr AS
SELECT
  c.billing_account_id,
  c.utility_id,
  c.istanza_utility_id,
  dbops.fn_pgtap_crea_articolo('PGTAP-LCP-' || substr(md5(clock_timestamp()::text), 1, 8)) AS articolo_id,
  (SELECT s.id
     FROM config.stati_doc_contratti s
    WHERE s.codice_interno = 'ATTIVO' AND s.attivo IS TRUE
    LIMIT 1
  ) AS stato_attivo_id,
  (SELECT s.id
     FROM config.stati_doc_contratti s
    WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE
    LIMIT 1
  ) AS stato_draft_id,
  (SELECT s.id
     FROM config.sorgenti s
    WHERE s.codice_interno = 'CONTRATTO' AND s.attivo IS TRUE
    LIMIT 1
  ) AS sorgente_tipo_id
FROM tmp_cli_contr c;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL
      AND utility_id IS NOT NULL
      AND istanza_utility_id IS NOT NULL
      AND articolo_id IS NOT NULL
      AND stato_attivo_id IS NOT NULL
      AND sorgente_tipo_id IS NOT NULL
   FROM tmp_refs_contr),
  'Riferimenti minimi disponibili'
);

-- ============================================================
-- 1) Contratto ATTIVO in validita restituito
-- ============================================================
CREATE TEMP TABLE tmp_contratto AS
WITH ins AS (
  INSERT INTO vendite.contratti (
    numero, billing_account_id, istanza_utility_id,
    utility_id, valido_dal, valido_al,
    stato_doc_contratto_id, data, meta
  )
  SELECT
    'PGTAP-CONTR-' || substr(md5(clock_timestamp()::text), 1, 8),
    r.billing_account_id, r.istanza_utility_id,
    r.utility_id,
    DATE '2026-06-01', DATE '2026-12-31',
    r.stato_draft_id, DATE '2026-06-01',
    jsonb_build_object('test_scope', 'pgtap_fn_list_contr')
  FROM tmp_refs_contr r
  RETURNING id, uid, valido_dal, data
)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_contratto_riga AS
WITH ins AS (
-- 🔴 COLONNA RINOMINATA, corretto il 2026-08-18.
--   `quantita_fissa` non esiste piu': il `20260511-31` l'ha RINOMINATA in
--   `quantita` (prerequisito di `contratti_righe_componenti`, pattern BoM CASO
--   A: le helper generiche `script.*` assumono che sul padre la colonna si
--   chiami `quantita`). L'INSERT falliva in parsing e il file non eseguiva
--   nessuna asserzione.
--   ⚠️ E dietro ce n'era una seconda: `fonte_quantita_attesa` e' NOT NULL senza
--   default. E' il concetto che ha ereditato il significato del vecchio nome —
--   `FISSA` e' letteralmente «la quantita' e' quella scritta qui» — ed e' il
--   valore di 23 righe su 24 in tabella. ⚠️ Non e' libero: il CHECK
--   `chk_contrighe_coerenza_fonte_erogazione` lo incrocia con `tipo_erogazione`.
  -- 🔴 tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04
  --   (brief-db-erogazione-obbligatoria-righe-fatturate). UNA_TANTUM e non
  --   CANONE: il test 3 deve vedere il valore della RIGA, e CANONE era anche il
  --   vecchio ripiego del lister — con quello il test passerebbe per coincidenza.
  INSERT INTO vendite.contratti_righe (
    contratto_id, articolo_id, prezzo_unitario, tipo_erogazione,
    qta_operativa, quantita, fonte_quantita_attesa, tipo_eccezione, attivo, meta
  )
  SELECT
    c.id, r.articolo_id, 50.000000, 'UNA_TANTUM',
    1.000000, 1.000000, 'FISSA',
    -- ⚠️ `tipo_eccezione` e' NOT NULL e il CHECK
    --   `chk_contrighe_prezzo_per_tipo_eccezione` lo lega al prezzo:
    --   ESCLUSIONE pretende prezzo NULL, OVERRIDE/AGGIUNTA lo pretendono
    --   valorizzato. Qui il prezzo c'e' (50), quindi ESCLUSIONE e' esclusa; fra
    --   le due che restano AGGIUNTA e' quella giusta — la riga aggiunge un
    --   articolo al contratto, non riscrive il prezzo di uno gia' a listino.
    'AGGIUNTA'::vendite.tipo_eccezione_contratto, true,
    jsonb_build_object('test_scope', 'pgtap_fn_list_contr')
  FROM tmp_contratto c, tmp_refs_contr r
  RETURNING id
)
SELECT * FROM ins;

-- 🔴 ATTIVAZIONE SPOSTATA IN CODA, 2026-08-18.
--   Il contratto nasceva gia' ATTIVO e le righe si inserivano dopo: da quando
--   esiste `trg_contratti_righe_a05_doc_righe_lock_fuori_bozza` (Step 2.3) quella
--   sequenza e' vietata — il pricing di un contratto attivo e' immutabile.
--   L'ordine giusto e' quello che segue anche l'applicazione: si compone in
--   DRAFT, poi si attiva. Lo stato finale del fixture non cambia (ATTIVO, che
--   e' cio' che `fn_list_contratti_da_pushare` deve vedere): cambia il momento
--   in cui ci si arriva.
--   ⚠️ Il secondo contratto del file nasceva gia' in DRAFT e resta com'e': li'
--   la sequenza era gia' quella giusta.
SELECT dbops.fn_pgtap_porta_a_stato('vendite.contratti'::regclass, id, 'ATTIVO')
  FROM tmp_contratto;

CREATE TEMP TABLE tmp_result_contr AS
SELECT *
FROM vendite.fn_list_contratti_da_pushare(NULL, NULL, NULL);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM tmp_result_contr rc
    WHERE rc.contratto_id = (SELECT id FROM tmp_contratto)
  ),
  'Contratto ATTIVO in validita restituito'
);

-- ============================================================
-- 2) Segment key include competenza_mese
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM tmp_result_contr rc
    WHERE rc.contratto_id = (SELECT id FROM tmp_contratto)
      AND rc.segment_key = 'CONTRATTO:' || (SELECT uid FROM tmp_contratto)::text
                            || ':R:' || (SELECT id FROM tmp_contratto_riga)::text
                            || ':M:' || to_char(
                                date_trunc('month',
                                  COALESCE(
                                    (SELECT valido_dal FROM tmp_contratto),
                                    (SELECT data FROM tmp_contratto)
                                  )
                                )::date,
                                'YYYY-MM'
                              )
  ),
  'Segment key include competenza_mese (CONTR:<uid>:R:<id>:M:<YYYY-MM>)'
);

-- ============================================================
-- 3) meta.tipo_erogazione = l'erogazione della riga
-- ============================================================
-- 🔴 Riscritto il 2026-10-13 (20261013-19): la colonna tipo_consumo, dove
--   finiva l'erogazione, e' ritirata (la madre la rifiutava). L'erogazione
--   viaggia in meta.tipo_erogazione, ed e' li' che si guarda.
-- 🔴 Riscritto il 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate R4).
--   Pinnava il ripiego COALESCE(tipo_erogazione, 'CANONE'): una riga senza
--   erogazione andava in fattura come canone senza che nessuno l'avesse scelto.
--   L'erogazione e' ora obbligatoria (CHECK + guard) e il lister la legge e basta.
SELECT ok(
  EXISTS (
    SELECT 1
    FROM tmp_result_contr rc
    WHERE rc.contratto_id = (SELECT id FROM tmp_contratto)
      AND rc.meta ->> 'tipo_erogazione' = 'UNA_TANTUM'
  ),
  'meta.tipo_erogazione = l''erogazione della riga (UNA_TANTUM), senza ripiego'
);

-- ============================================================
-- 4) prezzo_bloccato = TRUE quando prezzo_unitario presente
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM tmp_result_contr rc
    WHERE rc.contratto_id = (SELECT id FROM tmp_contratto)
      AND rc.prezzo_bloccato IS TRUE
      AND rc.prezzo_snapshot IS NOT NULL
  ),
  'prezzo_bloccato = TRUE quando prezzo_unitario presente'
);

-- ============================================================
-- 5) Contratto non ATTIVO escluso
-- ============================================================
CREATE TEMP TABLE tmp_contratto_draft AS
WITH ins AS (
  INSERT INTO vendite.contratti (
    numero, billing_account_id, istanza_utility_id,
    utility_id, valido_dal, valido_al,
    stato_doc_contratto_id, data, meta
  )
  SELECT
    'PGTAP-CONTR-D-' || substr(md5(clock_timestamp()::text), 1, 8),
    r.billing_account_id, r.istanza_utility_id,
    r.utility_id,
    DATE '2027-01-01', DATE '2027-06-30',
    COALESCE(r.stato_draft_id, r.stato_attivo_id), DATE '2027-01-01',
    jsonb_build_object('test_scope', 'pgtap_fn_list_contr', 'case', 'draft')
  FROM tmp_refs_contr r
  RETURNING id, uid
)
SELECT * FROM ins;

-- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
INSERT INTO vendite.contratti_righe (
  contratto_id, articolo_id, prezzo_unitario, tipo_erogazione,
  qta_operativa, quantita, fonte_quantita_attesa, tipo_eccezione, attivo, meta
)
SELECT
  -- rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.9, giro B3): l'articolo
  --   del builder e' MERCE, che ammette UNA_TANTUM; CANONE era scritto per caso.
  c.id, r.articolo_id, 30.000000, 'UNA_TANTUM',
  1.000000, 1.000000, 'FISSA',
  'AGGIUNTA'::vendite.tipo_eccezione_contratto, true,
  jsonb_build_object('test_scope', 'pgtap_fn_list_contr', 'case', 'draft')
FROM tmp_contratto_draft c, tmp_refs_contr r;

SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_contratti_da_pushare(NULL, NULL, NULL) rc
    WHERE rc.contratto_id = (SELECT id FROM tmp_contratto_draft)
  )
  OR (SELECT stato_draft_id IS NULL FROM tmp_refs_contr),
  'Contratto non ATTIVO escluso (o stato DRAFT non configurato)'
);

-- ============================================================
-- 6) Filtro p_billing_account_id rispettato
-- ============================================================
SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_contratti_da_pushare(NULL, -999999, NULL) rc
    WHERE rc.contratto_id = (SELECT id FROM tmp_contratto)
  ),
  'Filtro p_billing_account_id rispettato'
);

SELECT * FROM finish();
ROLLBACK;
