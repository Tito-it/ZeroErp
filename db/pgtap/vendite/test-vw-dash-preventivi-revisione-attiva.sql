-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13.5-ter, 2d): l'area della dashboard e' il codice della sorgente.
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i documenti nascono in
--   bozza e si portano avanti con dbops.fn_pgtap_porta_a_stato (prima le
--   revisioni nascevano gia' EMESSO/RIFIUTATO/ANNULLATO).
-- pgTAP test per Zero ERP
--
-- Test: regressione bug di vista "la vecchia revisione EMESSO riemerge come
--       documento aperto nei cruscotti" (brief-db-preventivi-revisione-attiva-
--       dashboard, fix 20260708-06 Opzione A).
--
--       Invariante: i resolver/union dashboard preventivi devono esporre SOLO
--       la revisione attiva del numero (derivazione canonica
--       vw_preventivi.is_attiva), MAI le revisioni superate rimaste in EMESSO.
--
--       Il fix cambia la SORGENTE di vw_dash_fatturazione_preventivi da
--       vendite.preventivi grezzo a vendite.vw_preventivi WHERE is_attiva.
--       Non introduce lo stato SUPERATO -> preserva il flusso voluto
--       "revisione annullata rifluisce al predecessore" (gestione-preventivi
--       §4.3), testato dallo scenario B.
--
--       Fixture (numeri multi-rev inseriti diretti, nati DRAFT e portati
--       allo stato scelto con dbops.fn_pgtap_porta_a_stato — rev 2026-10-24):
--         A) PGTAP-REVATT-A: rev0 EMESSO + rev1 RIFIUTATO
--            -> attiva = rev1 (negativa) -> 0 righe backlog/aperto, 1 sola riga
--               (RIFIUTATO) nella union; la rev0 EMESSO NON deve comparire.
--         B) PGTAP-REVATT-B: rev0 EMESSO + rev1 ANNULLATO
--            -> ANNULLATO e' abortito -> attiva = rev0 EMESSO (revert-on-abandon)
--               -> 1 riga = rev0 EMESSO; la rev1 ANNULLATO NON deve comparire.
--         C) PGTAP-REVATT-C: rev0 EMESSO singola -> compare 1 volta (no regressione).
--
-- Indice test (0..11):
--   0)  Precondizioni: refs minimi (BA, emittente, valuta, stati)
--   1)  Vista vw_dash_fatturazione_preventivi + derivazione vw_preventivi.is_attiva
--   2)  Setup scope operatore (GUC per il ramo commesse della union)
--   3)  A: vw_preventivi.is_attiva canonico (rev1 attiva, rev0 no)
--   4)  A: union espone SOLO la rev attiva (1 riga, stato RIFIUTATO, no EMESSO)
--   5)  A: backlog = 0 righe per il numero
--   6)  A: situazione aperta = 0 righe per il numero
--   7)  B: is_attiva unico e allineato a §4.3 (rev0 attiva, rev1 ANNULLATO no)
--   8)  B: union espone SOLO rev0 EMESSO (1 riga, no ANNULLATO)
--   9)  B: backlog espone rev0 EMESSO come IN_ATTESA_ACCETTAZIONE
--   10) C: preventivo singola-rev EMESSO compare 1 volta (no regressione)
--   11) D: preventivo singola-rev ANNULLATO -> is_attiva=FALSE e assente dalla
--       union (nuovo comportamento voluto dal self-term 20260708-07)
--   12) Invariante generale: nessun documento_id area PREVENTIVI non-attivo
--       nella union (per i fixture del test)
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

SELECT plan(13);

-- ============================================================
-- 0) Riferimenti minimi
-- ============================================================
CREATE TEMP TABLE tmp_ra_refs AS
SELECT
  (SELECT ba.id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND ba.soggetto_ruolo_id IS NOT NULL ORDER BY ba.id LIMIT 1) AS billing_account_id,
  (SELECT ba.utility_id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND ba.soggetto_ruolo_id IS NOT NULL ORDER BY ba.id LIMIT 1) AS utility_id,
  (SELECT ba.istanza_utility_id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND ba.soggetto_ruolo_id IS NOT NULL ORDER BY ba.id LIMIT 1) AS istanza_utility_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef WHERE ef.attivo IS TRUE
    ORDER BY ef.id LIMIT 1) AS emittente_fiscale_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'EMESSO' AND s.attivo IS TRUE LIMIT 1) AS st_emesso_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'RIFIUTATO' AND s.attivo IS TRUE LIMIT 1) AS st_rifiutato_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'ANNULLATO' AND s.attivo IS TRUE LIMIT 1) AS st_annullato_id;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL AND emittente_fiscale_id IS NOT NULL
      AND valuta_id IS NOT NULL AND st_emesso_id IS NOT NULL
      AND st_rifiutato_id IS NOT NULL AND st_annullato_id IS NOT NULL
     FROM tmp_ra_refs),
  '0. Precondizioni: refs minimi presenti (BA, emittente, valuta, stati EMESSO/RIFIUTATO/ANNULLATO)'
);

-- ============================================================
-- 1) Vista union sorgente + derivazione canonica esistono
-- ============================================================
SELECT ok(
  EXISTS (SELECT 1 FROM pg_views
           WHERE schemaname = 'vendite'
             AND viewname   = 'vw_dash_fatturazione_preventivi')
  AND EXISTS (SELECT 1 FROM information_schema.columns c
               WHERE c.table_schema = 'vendite'
                 AND c.table_name   = 'vw_preventivi'
                 AND c.column_name  = 'is_attiva'),
  '1. vw_dash_fatturazione_preventivi esiste e vw_preventivi espone is_attiva (derivazione canonica)'
);

-- ============================================================
-- 2) Setup scope operatore: la union include il ramo commesse che scopa per
--    current_setting(app.current_user_id) -> serve una GUC valida.
-- ============================================================
CREATE TEMP TABLE tmp_ra_op AS
SELECT id.auth_user_id AS user_id
  FROM anagrafiche.identita_digitali id
 WHERE id.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
   AND id.attivo = true
   AND NOT EXISTS (
       SELECT 1 FROM config.profili_accesso_bindings pab
       JOIN config.profili_accesso pa ON pa.id = pab.profilo_accesso_id
       WHERE pab.identita_digitale_id = id.id
         AND pab.attivo = true
         AND pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso)
 ORDER BY id.id LIMIT 1;

SELECT ok(
  (SELECT user_id IS NOT NULL FROM tmp_ra_op),
  '2. Trovato un operatore OPERATORE non-super per lo scope'
);

-- Garantisce che l'emittente dei fixture sia nello scope dell'operatore
-- (robustezza indipendente dal ruolo di sessione: le viste sono security_invoker).
SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on';
DELETE FROM config.user_emittenti_fiscali
 WHERE auth_user_id = (SELECT user_id FROM tmp_ra_op);
SET LOCAL zeroerp.allow_user_emittente_delete_override = '';

INSERT INTO config.user_emittenti_fiscali (auth_user_id, emittente_fiscale_id, meta)
SELECT o.user_id, r.emittente_fiscale_id,
       '{"test_scope":"pgtap_dash_revisione_attiva"}'::jsonb
  FROM tmp_ra_op o, tmp_ra_refs r
 WHERE o.user_id IS NOT NULL;

SELECT set_config('app.current_user_id',
    (SELECT user_id::text FROM tmp_ra_op), true);

-- ============================================================
-- Fixture A) PGTAP-REVATT-A: rev0 EMESSO + rev1 RIFIUTATO (attiva = rev1)
-- ============================================================
CREATE TEMP TABLE tmp_ra_a_rev0 AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-REVATT-A', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_dash_revisione_attiva'), r.emittente_fiscale_id
    FROM tmp_ra_refs r
  RETURNING id)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_ra_a_rev1 AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-REVATT-A', 1, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_dash_revisione_attiva'), r.emittente_fiscale_id
    FROM tmp_ra_refs r
  RETURNING id)
SELECT id FROM ins;

-- ============================================================
-- Fixture B) PGTAP-REVATT-B: rev0 EMESSO + rev1 ANNULLATO (attiva = rev0)
-- ============================================================
CREATE TEMP TABLE tmp_ra_b_rev0 AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-REVATT-B', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_dash_revisione_attiva'), r.emittente_fiscale_id
    FROM tmp_ra_refs r
  RETURNING id)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_ra_b_rev1 AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-REVATT-B', 1, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_dash_revisione_attiva'), r.emittente_fiscale_id
    FROM tmp_ra_refs r
  RETURNING id)
SELECT id FROM ins;

-- ============================================================
-- Fixture C) PGTAP-REVATT-C: rev0 EMESSO singola (no regressione)
-- ============================================================
CREATE TEMP TABLE tmp_ra_c_rev0 AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-REVATT-C', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_dash_revisione_attiva'), r.emittente_fiscale_id
    FROM tmp_ra_refs r
  RETURNING id)
SELECT id FROM ins;

-- ============================================================
-- Fixture D) PGTAP-REVATT-D: rev0 ANNULLATO singola (comportamento voluto:
-- annullato = non attivo, fuori dai cruscotti).
-- ============================================================
CREATE TEMP TABLE tmp_ra_d_rev0 AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id, data,
    fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-REVATT-D', 0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id,
         DATE '2080-01-01', false, false,
         jsonb_build_object('test_scope','pgtap_dash_revisione_attiva'), r.emittente_fiscale_id
    FROM tmp_ra_refs r
  RETURNING id)
SELECT id FROM ins;

-- ============================================================
-- Stato delle fixture (rev 2026-10-24, brief-modello-documento-vendita N-1):
--   le revisioni nascono DRAFT (lo stato non si scrive: lo mette il trigger
--   della nascita) e si portano allo stato del caso per la matrice, sotto i
--   guard veri: senza righe non hanno motivi da sollevare. Prima la rev 0,
--   poi la rev 1, come nel flusso vero. RIFIUTATO passa da EMESSO; ANNULLATO
--   esce direttamente dalla bozza (DRAFT -> ANNULLATO).
-- ============================================================
DO $porta$ BEGIN
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_ra_a_rev0), 'EMESSO');
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_ra_a_rev1), 'RIFIUTATO');
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_ra_b_rev0), 'EMESSO');
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_ra_b_rev1), 'ANNULLATO');
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_ra_c_rev0), 'EMESSO');
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_ra_d_rev0), 'ANNULLATO');
END $porta$;

-- ============================================================
-- 3) A: derivazione canonica corretta (rev1 attiva, rev0 no)
-- ============================================================
SELECT ok(
  (SELECT is_attiva FROM vendite.vw_preventivi WHERE id = (SELECT id FROM tmp_ra_a_rev1)) IS TRUE
  AND
  (SELECT is_attiva FROM vendite.vw_preventivi WHERE id = (SELECT id FROM tmp_ra_a_rev0)) IS FALSE,
  '3. A: vw_preventivi.is_attiva = rev1 RIFIUTATO attiva, rev0 EMESSO non attiva'
);

-- ============================================================
-- 4) A: union espone SOLO la revisione attiva (1 riga, RIFIUTATO, no EMESSO)
-- ============================================================
SELECT ok(
  (SELECT count(*) = 1
      AND bool_and(d.stato_codice_interno = 'RIFIUTATO')
      AND count(*) FILTER (WHERE d.stato_codice_interno = 'EMESSO') = 0
     FROM vendite.vw_dash_fatturazione_documenti d
    WHERE d.area = 'PREVENTIVO' AND d.codice = 'PGTAP-REVATT-A'),
  '4. A: la union mostra 1 sola riga = rev attiva RIFIUTATO; la rev0 EMESSO superata NON compare (no fantasma)'
);

-- ============================================================
-- 5) A: backlog = 0 righe (rev attiva negativa -> esclusa; nessun fantasma)
-- ============================================================
SELECT is(
  (SELECT count(*)::integer FROM vendite.vw_dash_backlog_documenti b
    WHERE b.area = 'PREVENTIVO'
      AND b.documento_id IN ((SELECT id FROM tmp_ra_a_rev0), (SELECT id FROM tmp_ra_a_rev1))),
  0,
  '5. A: Backlog = 0 righe per il numero (rev attiva RIFIUTATA esclusa, rev0 EMESSO non piu'' fantasma)'
);

-- ============================================================
-- 6) A: situazione aperta = 0 righe
-- ============================================================
SELECT is(
  (SELECT count(*)::integer FROM vendite.vw_dash_aperto_documenti a
    WHERE a.area = 'PREVENTIVO'
      AND a.documento_id IN ((SELECT id FROM tmp_ra_a_rev0), (SELECT id FROM tmp_ra_a_rev1))),
  0,
  '6. A: Situazione aperta = 0 righe per il numero (nessuna riga fantasma)'
);

-- ============================================================
-- 7) B: is_attiva unico e allineato alla spec (gestione-preventivi §4.3) dopo
--    il self-term (20260708-07): rev0 EMESSO attiva (revert-on-abandon: il
--    predecessore torna il documento vivo), rev1 ANNULLATO NON attiva (il suo
--    stato e' abortito, non si auto-dichiara piu' attiva stando in cima).
-- ============================================================
SELECT ok(
  (SELECT is_attiva FROM vendite.vw_preventivi WHERE id = (SELECT id FROM tmp_ra_b_rev0)) IS TRUE
  AND
  (SELECT is_attiva FROM vendite.vw_preventivi WHERE id = (SELECT id FROM tmp_ra_b_rev1)) IS FALSE,
  '7. B: vw_preventivi.is_attiva = rev0 EMESSO attiva (revert-on-abandon), rev1 ANNULLATO non attiva'
);

-- ============================================================
-- 8) B: union espone SOLO rev0 EMESSO (1 riga); la rev1 ANNULLATO, ora
--    is_attiva=FALSE, e' filtrata dal predicato WHERE is_attiva del resolver.
-- ============================================================
SELECT ok(
  (SELECT count(*) = 1
      AND bool_and(d.stato_codice_interno = 'EMESSO')
      AND bool_and(d.documento_id = (SELECT id FROM tmp_ra_b_rev0))
     FROM vendite.vw_dash_fatturazione_documenti d
    WHERE d.area = 'PREVENTIVO' AND d.codice = 'PGTAP-REVATT-B'),
  '8. B: la union mostra 1 sola riga = rev0 EMESSO (predecessore vivo); la rev1 ANNULLATO NON compare'
);

-- ============================================================
-- 9) B: backlog espone rev0 EMESSO come IN_ATTESA_ACCETTAZIONE
-- ============================================================
SELECT ok(
  (SELECT b.motivo_fermo = 'IN_ATTESA_ACCETTAZIONE'
     FROM vendite.vw_dash_backlog_documenti b
    WHERE b.area = 'PREVENTIVO'
      AND b.documento_id = (SELECT id FROM tmp_ra_b_rev0))
  AND NOT EXISTS (
    SELECT 1 FROM vendite.vw_dash_backlog_documenti b
     WHERE b.area = 'PREVENTIVO'
       AND b.documento_id = (SELECT id FROM tmp_ra_b_rev1)),
  '9. B: Backlog espone rev0 EMESSO (IN_ATTESA_ACCETTAZIONE); la rev1 ANNULLATO assente'
);

-- ============================================================
-- 10) C: preventivo singola-rev EMESSO compare 1 volta (no regressione)
-- ============================================================
SELECT is(
  (SELECT count(*)::integer FROM vendite.vw_dash_fatturazione_documenti d
    WHERE d.area = 'PREVENTIVO' AND d.codice = 'PGTAP-REVATT-C'),
  1,
  '10. C: preventivo singola-rev EMESSO compare esattamente 1 volta (nessuna regressione sul caso normale)'
);

-- ============================================================
-- 11) D: preventivo ANNULLATO singola-rev -> is_attiva=FALSE (self-term) e
--     assente dalla union (il resolver filtra WHERE is_attiva).
-- ============================================================
SELECT ok(
  (SELECT is_attiva FROM vendite.vw_preventivi
    WHERE id = (SELECT id FROM tmp_ra_d_rev0)) IS FALSE
  AND
  (SELECT count(*)::integer FROM vendite.vw_dash_fatturazione_documenti d
    WHERE d.area = 'PREVENTIVO' AND d.codice = 'PGTAP-REVATT-D') = 0,
  '11. D: annullato singola-rev is_attiva=FALSE e fuori dalla union (annullato = non attivo)'
);

-- ============================================================
-- 12) Invariante generale: ogni documento_id (area PREVENTIVI) esposto dalla
--     union per i fixture del test e' la revisione attiva secondo vw_preventivi.
-- ============================================================
SELECT is(
  (SELECT count(*)::integer
     FROM vendite.vw_dash_fatturazione_documenti d
     JOIN vendite.vw_preventivi p ON p.id = d.documento_id
    WHERE d.area = 'PREVENTIVO'
      AND d.codice LIKE 'PGTAP-REVATT-%'
      AND p.is_attiva IS FALSE),
  0,
  '12. Invariante: nessuna revisione non-attiva compare nella union dashboard'
);

SELECT * FROM finish();
ROLLBACK;
