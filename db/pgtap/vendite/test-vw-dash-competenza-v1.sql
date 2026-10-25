-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): il file pescava dal database BA, articolo, emittente, registro e un operatore (rosso in partenza: «billing_account_id nullo» sulla commessa); ora il mondo da dbops.fn_pgtap_crea_mondo_cliente, la commessa da dbops.fn_pgtap_crea_commessa, la fattura da dbops.fn_pgtap_crea_fattura; il reset del test 13 e' il verbo vero vendite.fn_cleanup_fatture_by_ids (E-4: attesa dichiarata, test spostato in coda). Restano a mano le attivita' nei loro stati, le attivita' fatturabili col data_insert, la riga di fattura e i lotti: sono il caso.
-- pgTAP test per Zero ERP
--
-- Test: viste Lente 1 Competenza (20260706-09..11 + indice -14):
--       vw_dash_competenza_attivita (dettaglio grana attivita', stadi funnel,
--       recuperi tardivi da attivita_fatturabili.data_insert),
--       vw_dash_competenza_mensile (aggregata formato lungo),
--       vw_dash_competenza_errori (task run ERRORE vivi + fatture critical).
--       Brief: brief-db-fatturazione-due-lenti §4 e §7.
--       Fixture (costruita: mondo, commessa e fattura dai builder): commessa
--       (emittente A) con 4 attivita' 2080-01 nei 4 stadi
--       (10/20/30/40) + 1 void ANNULLATA; fattura BOZZA collegata; lotto
--       2080-04 con task run in ERRORE.
--
-- Indice test (0..16):
--   0)  Precondizioni (refs costruiti: BA, articolo, stati, emittente A)
--   1)  Le 3 viste vw_dash_competenza_* esistono
--   2)  Setup: operatore OPERATORE non-super trovato (scope fail-closed)
--   3)  Stadio DA_APPROVARE (BOZZA/NON_EMESSA, valore 10)
--   4)  Stadio DA_EMETTERE (APPROVATA/NON_EMESSA, valore 20)
--   5)  Stadio EMESSA_NON_FATTURATA (AF senza fattura, in tempo, valore 30)
--   6)  Stadio FATTURATA (AF agganciata, emessa in RITARDO, stato fattura,
--       valore_fatturato 40)
--   7)  Void ANNULLATA esclusa dal dettaglio (predicato 20260703-61)
--   8)  Mensile 2080-01: 4 righe formato lungo, valori e n_in_ritardo coerenti
--   9)  ERRORI: task run ERRORE vivo -> riga TASK_ERRORE col mese del lotto
--   10) ERRORI: retry COMPLETATO successivo spegne il TASK_ERRORE
--   11) ERRORI: fattura critical -> FATTURA_CRITICA con competenza dai mesi AF
--   12) ERRORI: critical=false spegne la FATTURA_CRITICA
--   14) commessa_stato_descrizione sul dettaglio (20260815-24)
--   15) commessa_stato_descrizione e documento_id sui gruppi (20260815-25)
--   15-bis..septies) il documento trattenuto da un lotto vivo
--   13) SENTINELLA C1/reset (DL-5): dopo il reset vero
--       (vendite.fn_cleanup_fatture_by_ids) data_insert INVARIATA, stadio
--       torna DA_EMETTERE, ritardo resta (in coda dal 2026-10-25, E-4)
--   16) FAIL-CLOSED: GUC vuota -> 0 righe in dettaglio e mensile
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
-- ⛔ rev 2026-10-25 (giro D-4): il mondo si COSTRUISCE (azienda, operatore
--   OPERATORE non-super, cliente BA): il file pescava BA, articolo, emittente
--   e operatore dal database, ed era rosso in partenza su un DB senza dati.
--   Il builder apre da se' il contesto sul suo operatore: la riga lo dichiara.
CREATE TEMP TABLE tmp_dc_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP dash competenza');
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM tmp_dc_mondo)); END $ctx$;

SELECT plan(23);

-- ============================================================
-- 0) Riferimenti minimi
-- ============================================================
-- La commessa del cliente, dalla madre: codice, emittente e stato li decide
-- il dominio (prima: INSERT a mano col primo stato e il primo emittente).
CREATE TEMP TABLE tmp_dc_cm AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('dash competenza', NULL,
                  (SELECT billing_account_id FROM tmp_dc_mondo));

CREATE TEMP TABLE tmp_dc_refs AS
SELECT
  m.billing_account_id,
  m.istanza_utility_id,
  dbops.fn_pgtap_crea_articolo('PGTAP-DC-ART', false) AS articolo_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE
    ORDER BY t.id LIMIT 1) AS tipo_doc_fiscale_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  -- Lo stato e l'emittente della commessa costruita (i test 14-15 li leggono).
  c.stato_commessa_id,
  c.emittente_soggetto_ruolo_id AS ef_a_sr,
  -- La fattura nasce in bozza dal builder.
  (SELECT s.id FROM config.stati_doc_fiscale s WHERE s.codice_interno = 'DRAFT') AS stato_fiscale_id,
  'DRAFT'::varchar AS stato_fiscale_ci
FROM tmp_dc_mondo m, tmp_dc_cm c;

-- L'unita' di misura e' quella dell'articolo costruito.
ALTER TABLE tmp_dc_refs ADD COLUMN uom_id bigint;
UPDATE tmp_dc_refs r SET uom_id = (SELECT a.uom_id FROM catalogo.articoli a WHERE a.id = r.articolo_id);

SELECT ok(
  (SELECT billing_account_id IS NOT NULL AND articolo_id IS NOT NULL
      AND uom_id IS NOT NULL AND tipo_doc_fiscale_id IS NOT NULL
      AND stato_commessa_id IS NOT NULL AND ef_a_sr IS NOT NULL
      AND stato_fiscale_id IS NOT NULL
     FROM tmp_dc_refs),
  '0. Precondizioni soddisfatte'
);

-- ============================================================
-- 1) Le 3 viste esistono
-- ============================================================
SELECT is(
  (SELECT count(*)::integer FROM pg_views
    WHERE schemaname = 'vendite'
      AND viewname IN ('vw_dash_competenza_attivita',
                       'vw_dash_competenza_mensile',
                       'vw_dash_competenza_errori')),
  3,
  '1. Le 3 viste vw_dash_competenza_* esistono'
);

-- ============================================================
-- 2) Setup scope: le viste della Lente 1 sono FAIL-CLOSED (senza GUC
--    operatore -> 0 righe). Operatore OPERATORE non-super whitelistato su A.
-- ============================================================
-- L'operatore e' quello del mondo costruito, gia' abilitato sul suo emittente:
-- la condizione resta quella di prima (OPERATORE, attivo, non super).
CREATE TEMP TABLE tmp_dc_op AS
SELECT id.auth_user_id AS user_id
  FROM anagrafiche.identita_digitali id
 WHERE id.auth_user_id = (SELECT auth_user_id FROM tmp_dc_mondo)
   AND id.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
   AND id.attivo = true
   AND NOT EXISTS (
       SELECT 1 FROM config.profili_accesso_bindings pab
       JOIN config.profili_accesso pa ON pa.id = pab.profilo_accesso_id
       WHERE pab.identita_digitale_id = id.id
         AND pab.attivo = true
         AND pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso)
 ORDER BY id.id LIMIT 1;

SELECT ok(
  (SELECT user_id IS NOT NULL FROM tmp_dc_op),
  '2. Trovato un operatore OPERATORE non-super per lo scope'
);

-- ============================================================
-- Fixture: commessa (emittente A) + 4 attivita' 2080-01 (una per stadio)
-- + 1 void ANNULLATA. Valori 10/20/30/40 (+999 void).
-- ============================================================
CREATE TEMP TABLE tmp_dc_commessa AS
SELECT c.commessa_id AS id FROM tmp_dc_cm c;

-- Le 4 attivita' + la void, con slot per il lookup nei test.
CREATE TEMP TABLE tmp_dc_att (slot text, attivita_id bigint);

WITH ins AS (
  INSERT INTO vendite.commesse_attivita (
    commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
    uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
    tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
    stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
  SELECT (SELECT id FROM tmp_dc_commessa),
         'PGTAP-DC-A1-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.articolo_id, r.istanza_utility_id, DATE '2080-01-01', r.uom_id, 1,
         DATE '2080-01-01', DATE '2080-01-01', DATE '2080-01-31',
         r.tipo_doc_fiscale_id, r.valuta_id, 10.000000, 'FIXED',
         'BOZZA', 'NON_EMESSA', (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
         ((SELECT id FROM tmp_dc_commessa))::text
    FROM tmp_dc_refs r
  RETURNING id)
INSERT INTO tmp_dc_att SELECT 'A1_DA_APPROVARE', id FROM ins;

WITH ins AS (
  INSERT INTO vendite.commesse_attivita (
    commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
    uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
    tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
    stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid,
    tipo_movimento)
  SELECT (SELECT id FROM tmp_dc_commessa),
         'PGTAP-DC-A2-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.articolo_id, r.istanza_utility_id, DATE '2080-01-01', r.uom_id, 1,
         DATE '2080-01-01', DATE '2080-01-01', DATE '2080-01-31',
         r.tipo_doc_fiscale_id, r.valuta_id, 20.000000, 'FIXED',
         -- ⭐ SENZA sorgente, di proposito: e' il gruppo sourceless del test 15
         --   ('MAN:<commessa>'). Sul modello una riga senza sorgente e' una
         --   RETTIFICA o un ONERE (vincolo 20261012-27): RETTIFICA, perche'
         --   l'ONERE vorrebbe una causale e un articolo d'onere dal catalogo.
         'APPROVATA', 'NON_EMESSA', NULL, NULL,
         'RETTIFICA'
    FROM tmp_dc_refs r
  RETURNING id)
INSERT INTO tmp_dc_att SELECT 'A2_DA_EMETTERE', id FROM ins;

WITH ins AS (
  INSERT INTO vendite.commesse_attivita (
    commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
    uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
    tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
    stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
  SELECT (SELECT id FROM tmp_dc_commessa),
         'PGTAP-DC-A3-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.articolo_id, r.istanza_utility_id, DATE '2080-01-01', r.uom_id, 1,
         DATE '2080-01-01', DATE '2080-01-01', DATE '2080-01-31',
         r.tipo_doc_fiscale_id, r.valuta_id, 30.000000, 'FIXED',
         'APPROVATA', 'EMESSA', (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
         ((SELECT id FROM tmp_dc_commessa))::text
    FROM tmp_dc_refs r
  RETURNING id)
INSERT INTO tmp_dc_att SELECT 'A3_EMESSA', id FROM ins;

WITH ins AS (
  INSERT INTO vendite.commesse_attivita (
    commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
    uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
    tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
    stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
  SELECT (SELECT id FROM tmp_dc_commessa),
         'PGTAP-DC-A4-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.articolo_id, r.istanza_utility_id, DATE '2080-01-01', r.uom_id, 1,
         DATE '2080-01-01', DATE '2080-01-01', DATE '2080-01-31',
         r.tipo_doc_fiscale_id, r.valuta_id, 40.000000, 'FIXED',
         'APPROVATA', 'EMESSA', (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
         ((SELECT id FROM tmp_dc_commessa))::text
    FROM tmp_dc_refs r
  RETURNING id)
INSERT INTO tmp_dc_att SELECT 'A4_FATTURATA', id FROM ins;

WITH ins AS (
  INSERT INTO vendite.commesse_attivita (
    commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
    uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
    tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
    stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
  SELECT (SELECT id FROM tmp_dc_commessa),
         'PGTAP-DC-A5-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.articolo_id, r.istanza_utility_id, DATE '2080-01-01', r.uom_id, 1,
         DATE '2080-01-01', DATE '2080-01-01', DATE '2080-01-31',
         r.tipo_doc_fiscale_id, r.valuta_id, 999.000000, 'FIXED',
         'APPROVATA', 'ANNULLATA', (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
         ((SELECT id FROM tmp_dc_commessa))::text
    FROM tmp_dc_refs r
  RETURNING id)
INSERT INTO tmp_dc_att SELECT 'A5_VOID', id FROM ins;

-- Fattura BOZZA (senza numero) dal builder + la riga a mano: destinazione
-- dell'AF di A4, scritta a mano col suo data_insert (il ritardo e' il caso).
CREATE TEMP TABLE tmp_dc_fattura AS
SELECT f.fattura_id AS id
  FROM dbops.fn_pgtap_crea_fattura('dash competenza', 'DRAFT',
           (SELECT billing_account_id FROM tmp_dc_refs)) f;

CREATE TEMP TABLE tmp_dc_fattura_riga AS
WITH ins AS (
  INSERT INTO vendite.fatture_righe (
    fattura_id, riga_nr, descrizione, qta, prezzo_unitario, imponibile_riga, competenza_dal, competenza_al)
  SELECT (SELECT id FROM tmp_dc_fattura), 1,
         'PGTAP dash competenza', 1, 40.000000, 40.000000, script.fn_data_operativa(), script.fn_data_operativa()
  RETURNING id)
SELECT id FROM ins;

-- AF per A3 (emessa IN TEMPO: data_insert nel mese di competenza) e per A4
-- (emessa in RITARDO: data_insert 2080-03, competenza 2080-01) agganciata
-- alla riga fattura. data_insert esplicita: il DEFAULT now() vale solo se
-- omessa e nessun trigger la tocca (validazione DL-5).
INSERT INTO vendite.attivita_fatturabili (
  articolo_id, istanza_utility_id, data_attivita, quantita,
  competenza_mese, competenza_dal, competenza_al,
  uom_id, valuta_id, prezzo_unitario, tipo_doc_fiscale_id,
  commessa_id, commessa_attivita_id, data_insert,
  -- ⭐ billing_account_id: NOT NULL dal changeSet 20260910-25. Si deriva
  --   dalla COMMESSA, che e' la rotta portante (commessa_id NOT NULL ->
  --   commesse.billing_account_id NOT NULL): la fixture non lo inventa.
  billing_account_id)
SELECT r.articolo_id, r.istanza_utility_id, DATE '2080-01-01', 1,
       DATE '2080-01-01', DATE '2080-01-01', DATE '2080-01-31',
       r.uom_id, r.valuta_id, 30.000000, r.tipo_doc_fiscale_id,
       (SELECT id FROM tmp_dc_commessa),
       (SELECT attivita_id FROM tmp_dc_att WHERE slot = 'A3_EMESSA'),
       TIMESTAMPTZ '2080-01-05 10:00:00+00',
       (SELECT c.billing_account_id FROM vendite.commesse c
         WHERE c.id = (SELECT id FROM tmp_dc_commessa))
       FROM tmp_dc_refs r;

INSERT INTO vendite.attivita_fatturabili (
  articolo_id, istanza_utility_id, data_attivita, quantita,
  competenza_mese, competenza_dal, competenza_al,
  uom_id, valuta_id, prezzo_unitario, tipo_doc_fiscale_id,
  commessa_id, commessa_attivita_id, fattura_riga_id, data_insert,
  -- ⭐ billing_account_id: NOT NULL dal changeSet 20260910-25. Si deriva
  --   dalla COMMESSA, che e' la rotta portante (commessa_id NOT NULL ->
  --   commesse.billing_account_id NOT NULL): la fixture non lo inventa.
  billing_account_id)
SELECT r.articolo_id, r.istanza_utility_id, DATE '2080-01-01', 1,
       DATE '2080-01-01', DATE '2080-01-01', DATE '2080-01-31',
       r.uom_id, r.valuta_id, 40.000000, r.tipo_doc_fiscale_id,
       (SELECT id FROM tmp_dc_commessa),
       (SELECT attivita_id FROM tmp_dc_att WHERE slot = 'A4_FATTURATA'),
       (SELECT id FROM tmp_dc_fattura_riga),
       TIMESTAMPTZ '2080-03-15 10:00:00+00',
       (SELECT c.billing_account_id FROM vendite.commesse c
         WHERE c.id = (SELECT id FROM tmp_dc_commessa))
       FROM tmp_dc_refs r;

-- ============================================================
-- 3-6) Stadi del funnel
-- ============================================================
SELECT ok(
  (SELECT v.stadio = 'DA_APPROVARE' AND v.valore = 10
      AND v.data_emissione IS NULL AND v.emessa_in_ritardo IS NULL
     FROM vendite.vw_dash_competenza_attivita v
    WHERE v.commessa_attivita_id = (SELECT attivita_id FROM tmp_dc_att WHERE slot = 'A1_DA_APPROVARE')),
  '3. A1 BOZZA/NON_EMESSA: stadio DA_APPROVARE, valore 10, nessuna emissione'
);

SELECT ok(
  (SELECT v.stadio = 'DA_EMETTERE' AND v.valore = 20
     FROM vendite.vw_dash_competenza_attivita v
    WHERE v.commessa_attivita_id = (SELECT attivita_id FROM tmp_dc_att WHERE slot = 'A2_DA_EMETTERE')),
  '4. A2 APPROVATA/NON_EMESSA: stadio DA_EMETTERE, valore 20'
);

SELECT ok(
  (SELECT v.stadio = 'EMESSA_NON_FATTURATA' AND v.valore = 30
      AND v.data_emissione = TIMESTAMPTZ '2080-01-05 10:00:00+00'
      AND v.emessa_in_ritardo = false
     FROM vendite.vw_dash_competenza_attivita v
    WHERE v.commessa_attivita_id = (SELECT attivita_id FROM tmp_dc_att WHERE slot = 'A3_EMESSA')),
  '5. A3 EMESSA senza fattura: stadio EMESSA_NON_FATTURATA, emessa IN TEMPO (2080-01)'
);

SELECT ok(
  (SELECT v.stadio = 'FATTURATA' AND v.valore = 40
      AND v.emessa_in_ritardo = true
      AND v.fattura_id = (SELECT id FROM tmp_dc_fattura)
      AND v.stato_fattura_codice_interno = (SELECT stato_fiscale_ci FROM tmp_dc_refs)
      AND v.valore_fatturato = 40
     FROM vendite.vw_dash_competenza_attivita v
    WHERE v.commessa_attivita_id = (SELECT attivita_id FROM tmp_dc_att WHERE slot = 'A4_FATTURATA')),
  '6. A4 FATTURATA: emessa in RITARDO (2080-03 su competenza 2080-01), stato fattura e valore_fatturato 40'
);

-- ============================================================
-- 7) Void esclusa
-- ============================================================
SELECT is(
  (SELECT count(*)::integer FROM vendite.vw_dash_competenza_attivita v
    WHERE v.commessa_attivita_id = (SELECT attivita_id FROM tmp_dc_att WHERE slot = 'A5_VOID')),
  0,
  '7. Attivita'' ANNULLATA (void) esclusa dal dettaglio (predicato 20260703-61)'
);

-- ============================================================
-- 8) Mensile formato lungo (perimetro: la nostra commessa e' l''unica con
--    competenza 2080-01 visibile all''operatore in questo DB di test? No:
--    filtriamo sui 4 stadi attesi con i valori della fixture, robusto anche
--    con altri dati nel mese grazie al confronto >=).
-- ============================================================
SELECT ok(
  (SELECT
      -- ogni stadio della fixture e' rappresentato nel formato lungo del mese
      EXISTS (SELECT 1 FROM vendite.vw_dash_competenza_mensile m
               WHERE m.competenza_mese = DATE '2080-01-01'
                 AND m.stadio = 'DA_APPROVARE' AND m.stato_fattura_codice_interno IS NULL
                 AND m.n_attivita >= 1 AND m.valore_tot >= 10)
      AND EXISTS (SELECT 1 FROM vendite.vw_dash_competenza_mensile m
               WHERE m.competenza_mese = DATE '2080-01-01'
                 AND m.stadio = 'DA_EMETTERE' AND m.stato_fattura_codice_interno IS NULL
                 AND m.n_attivita >= 1 AND m.valore_tot >= 20)
      AND EXISTS (SELECT 1 FROM vendite.vw_dash_competenza_mensile m
               WHERE m.competenza_mese = DATE '2080-01-01'
                 AND m.stadio = 'EMESSA_NON_FATTURATA' AND m.stato_fattura_codice_interno IS NULL
                 AND m.n_attivita >= 1 AND m.valore_tot >= 30)
      AND EXISTS (SELECT 1 FROM vendite.vw_dash_competenza_mensile m
               WHERE m.competenza_mese = DATE '2080-01-01'
                 AND m.stadio = 'FATTURATA'
                 AND m.stato_fattura_codice_interno = (SELECT stato_fiscale_ci FROM tmp_dc_refs)
                 AND m.n_attivita >= 1 AND m.valore_tot >= 40
                 AND m.valore_fatturato_tot >= 40 AND m.n_in_ritardo >= 1
                 AND m.valore_in_ritardo >= 40)),
  '8. Mensile 2080-01: i 4 stadi presenti in formato lungo con valori e ritardo coerenti'
);

-- ============================================================
-- Fixture ERRORI: lotto 2080-04 + task run in ERRORE.
-- ============================================================
CREATE TEMP TABLE tmp_dc_lotto AS
WITH ins AS (
  INSERT INTO vendite.fatturazione_lotti (
    codice, competenza_mese, tipo_doc_fiscale_id, emittente_soggetto_ruolo_id, meta)
  SELECT 'PGTAP-DC-LT-' || substr(md5(clock_timestamp()::text), 1, 8),
         DATE '2080-04-01', r.tipo_doc_fiscale_id, r.ef_a_sr,
         jsonb_build_object('test_scope','pgtap_dash_competenza')
    FROM tmp_dc_refs r
  RETURNING id)
SELECT id FROM ins;

INSERT INTO vendite.fatturazione_lotti_task_runs (
  lotto_id, task_code, tentativo, task_stato, started_at, ended_at,
  error_code, error_message)
SELECT (SELECT id FROM tmp_dc_lotto), 'PGTAP_TASK', 1, 'ERRORE',
       TIMESTAMPTZ '2080-04-02 10:00:00+00', TIMESTAMPTZ '2080-04-02 10:00:05+00',
       'E_PGTAP_TEST', 'errore simulato pgtap';

-- ============================================================
-- 9-10) Blocco errori: TASK_ERRORE vivo, poi spento dal retry
-- ============================================================
SELECT ok(
  (SELECT v.competenza_mese = DATE '2080-04-01'
      AND v.lotto_id = (SELECT id FROM tmp_dc_lotto)
      AND v.error_code = 'E_PGTAP_TEST'
      AND v.fattura_id IS NULL
     FROM vendite.vw_dash_competenza_errori v
    WHERE v.tipo_evento = 'TASK_ERRORE'
      AND v.lotto_id = (SELECT id FROM tmp_dc_lotto)),
  '9. Task run in ERRORE: riga TASK_ERRORE con la competenza del lotto (2080-04)'
);

INSERT INTO vendite.fatturazione_lotti_task_runs (
  lotto_id, task_code, tentativo, task_stato, started_at, ended_at)
SELECT (SELECT id FROM tmp_dc_lotto), 'PGTAP_TASK', 2, 'COMPLETATO',
       TIMESTAMPTZ '2080-04-02 11:00:00+00', TIMESTAMPTZ '2080-04-02 11:00:05+00';

SELECT is(
  (SELECT count(*)::integer FROM vendite.vw_dash_competenza_errori v
    WHERE v.tipo_evento = 'TASK_ERRORE'
      AND v.lotto_id = (SELECT id FROM tmp_dc_lotto)),
  0,
  '10. Retry COMPLETATO successivo (tentativo 2): il TASK_ERRORE si spegne'
);

-- ============================================================
-- 11-12) Blocco errori: FATTURA_CRITICA (competenza dai mesi AF: la fattura
--        fixture non e' in alcun lotto, la sua riga e' agganciata a un'AF di
--        competenza 2080-01 -> regola DB-7 livello b).
-- ============================================================
UPDATE vendite.fatture SET critical = true
 WHERE id = (SELECT id FROM tmp_dc_fattura);

SELECT ok(
  (SELECT v.competenza_mese = DATE '2080-01-01'
      AND v.lotto_id IS NULL
      AND v.fattura_id = (SELECT id FROM tmp_dc_fattura)
     FROM vendite.vw_dash_competenza_errori v
    WHERE v.tipo_evento = 'FATTURA_CRITICA'
      AND v.fattura_id = (SELECT id FROM tmp_dc_fattura)),
  '11. Fattura critical senza lotto: FATTURA_CRITICA con competenza dai mesi AF (2080-01)'
);

UPDATE vendite.fatture SET critical = false
 WHERE id = (SELECT id FROM tmp_dc_fattura);

SELECT is(
  (SELECT count(*)::integer FROM vendite.vw_dash_competenza_errori v
    WHERE v.tipo_evento = 'FATTURA_CRITICA'
      AND v.fattura_id = (SELECT id FROM tmp_dc_fattura)),
  0,
  '12. critical=false: la FATTURA_CRITICA si spegne'
);

-- ============================================================
-- 14-15) Decodifica di display dello stato commessa e id del documento
--        sorgente (20260815-24 / -25, richieste BE §8.3 e §9 F3 di
--        brief-db-emittibilita-visibile-e-sbloccabile). La convenzione del
--        progetto e' che le liste ricevano i campi di display gia' decodificati
--        dal DB: un codice interno a video e' il sintomo che la decodifica e'
--        finita lato client.
-- ============================================================
SELECT ok(
  (SELECT v.commessa_stato_descrizione
          = (SELECT COALESCE(sc.descrizione, sc.codice)
               FROM vendite.stati_commessa sc, tmp_dc_refs r
              WHERE sc.id = r.stato_commessa_id)
     FROM vendite.vw_dash_competenza_attivita v
    WHERE v.commessa_attivita_id = (SELECT attivita_id FROM tmp_dc_att WHERE slot = 'A2_DA_EMETTERE')),
  '14. Dettaglio: commessa_stato_descrizione decodificata accanto al codice interno'
);

-- ⚠️ Il gruppo DA_EMETTERE della fixture e' SOURCELESS (A2, una RETTIFICA con
--   sorgente NULL -> chiave 'MAN:<commessa>'), quindi `documento_id` e' NULL, ed e' il
--   comportamento voluto: quei gruppi un documento non ce l'hanno e il FE
--   offre la sola commessa. Il ramo con documento valorizzato ha bisogno di un
--   documento sorgente vero nella vista dei documenti: si verifica quando c'e',
--   e si dichiara skippato quando manca — un ok incondizionato qui sarebbe una
--   copertura solo apparente.
SELECT ok(
  (SELECT g.commessa_stato_descrizione
          = (SELECT COALESCE(sc.descrizione, sc.codice)
               FROM vendite.stati_commessa sc, tmp_dc_refs r
              WHERE sc.id = r.stato_commessa_id)
      AND g.documento_id IS NULL
      AND g.riferimento = g.commessa_codice
     FROM vendite.vw_dash_competenza_gruppi g
    WHERE g.commessa_id = (SELECT id FROM tmp_dc_commessa)
      AND g.stadio = 'DA_EMETTERE'),
  '15. Gruppi: commessa_stato_descrizione decodificata; documento_id NULL sul gruppo sourceless (oneri), col riferimento che ripiega sulla commessa'
);

-- ============================================================
-- 15-bis..quater) ⭐ IL DOCUMENTO TRATTENUTO DA UN LOTTO VIVO
-- ============================================================
-- ⛔ Perche' qui e non in un file suo: la riga di dashboard esiste solo con
--   questa fixture (commessa + attivita + operatore + GUC), e un presidio che
--   se la rifabbrica da zero sarebbe una seconda fixture che diverge.
-- ⚠️ E vanno PRIMA del test 16, che azzera la GUC: dopo, la vista non rende
--   righe e queste asserzioni passerebbero a vuoto.
--
-- ⭐ I tre test sono un verso e il suo contrario, e servono entrambi:
--     · lotto VIVO      -> la riga si spegne e il conteggio la toglie;
--     · lotto ANNULLATO -> la riga torna libera e il conteggio la riprende.
--   Con il solo primo, un predicato che blocca QUALUNQUE documento con un esito
--   passerebbe — ed e' l'errore che `ultimo_esito` fa davvero: su un lotto
--   annullato direbbe «bloccato» per un documento fatturabile.
--   Brief: brief-db-documento-trattenuto-da-un-lotto-vivo.md (T-2, T-3)

-- La riga da trattenere, con le chiavi con cui il riepilogo la raggruppa.
-- ⚠️ ORDER BY prima del LIMIT: senza, quale gruppo esca dipende dal planner.
CREATE TEMP TABLE tmp_dc_trat AS
SELECT g.gruppo_key, g.competenza_mese, g.stadio, g.emittente_soggetto_ruolo_id
  FROM vendite.vw_dash_competenza_gruppi g
 WHERE g.commessa_id = (SELECT id FROM tmp_dc_commessa)
   AND g.stadio = 'DA_EMETTERE'
 ORDER BY g.gruppo_key
 LIMIT 1;

-- Un lotto VIVO che tiene quel documento. ⛔ `codice_interno`, mai un id.
CREATE TEMP TABLE tmp_dc_lotto_vivo AS
WITH ins AS (
  INSERT INTO vendite.fatturazione_lotti (
    codice, competenza_mese, tipo_doc_fiscale_id, emittente_soggetto_ruolo_id,
    stato_doc_fiscale_id, meta)
  SELECT 'PGTAP-DC-TRAT-' || substr(md5(clock_timestamp()::text), 1, 8),
         t.competenza_mese, r.tipo_doc_fiscale_id, r.ef_a_sr,
         (SELECT s.id FROM config.stati_doc_fiscale s WHERE s.codice_interno = 'DRAFT'),
         jsonb_build_object('test_scope','pgtap_dash_competenza')
    FROM tmp_dc_refs r, tmp_dc_trat t
  RETURNING id)
SELECT id FROM ins;

INSERT INTO vendite.fatturazione_lotti_gruppi (lotto_id, gruppo_key)
SELECT (SELECT id FROM tmp_dc_lotto_vivo), t.gruppo_key FROM tmp_dc_trat t;

-- ⭐ Esito COMPLETED di proposito: e' il caso in cui `ultimo_esito` direbbe
--   «libero» e il documento e' invece trattenuto. Il verso che nessuno vedeva.
INSERT INTO vendite.fatturazione_lotti_esiti (lotto_id, gruppo_key, stato_esecuzione)
SELECT (SELECT id FROM tmp_dc_lotto_vivo), t.gruppo_key, 'COMPLETED' FROM tmp_dc_trat t;

SELECT is(
  (SELECT g.emissione_blocco_reason || '|' || g.emissione_blocco_lotto_codice
     FROM vendite.vw_dash_competenza_gruppi g, tmp_dc_trat t
    WHERE g.gruppo_key = t.gruppo_key AND g.stadio = t.stadio),
  'TRATTENUTO_DA_LOTTO|' || (SELECT l.codice FROM vendite.fatturazione_lotti l
                              WHERE l.id = (SELECT id FROM tmp_dc_lotto_vivo)),
  '15-bis. la riga si spegne col motivo e nomina il lotto che la trattiene (esito COMPLETED, lotto VIVO)'
);

-- ⭐ rev 2026-09-09 — IL CONTEGGIO SI LEGGE DOVE IL NUMERO VIVE.
--   Prima questa asserzione stava su vw_dash_competenza_gruppi_riepilogo, che
--   pero' NON e' la card: quella vista non la legge nessuno (misurato il
--   2026-09-09, zero consumatori) ed e' stata ritirata. La card e'
--   `vw_dash_competenza_mensile`, e il numero e' `n_attivita`.
-- ⛔ E' la §12.5.3 applicata a un numero invece che a un pulsante: si consegna
--   dove il numero VIENE LETTO, non dove parlerebbe della stessa cosa.
-- ⭐ Le due meta' contano entrambe: il numero CALA e la riga RESTA. Con una
--   `WHERE` al posto del `FILTER` il bucket sparirebbe, e sparirebbe con lui
--   la dichiarazione che spiega il calo.
SELECT results_eq(
  $$ SELECT count(*)::int AS righe,
            COALESCE(sum(m.n_attivita_trattenute), 0)::int AS trattenute
       FROM vendite.vw_dash_competenza_mensile m, tmp_dc_trat t
      WHERE m.competenza_mese = t.competenza_mese AND m.stadio = t.stadio $$,
  $$ VALUES (1, 1) $$,
  '15-ter. la card ESCLUDE la trattenuta e la DICHIARA, e il bucket non sparisce'
);

-- ============================================================
-- 15-quinquies) ⭐ Il verdetto e' SPENTO su cio' che e' gia' fatturato
-- ============================================================
-- ⛔ E' il difetto §6.3 del brief: un documento appena fatturato ha esito
--   COMPLETED sul PROPRIO lotto, che resta DRAFT fino a «Rendi definitive».
--   Un verdetto che guardasse l'esito invece della CLASSE lo direbbe
--   «trattenuto» — e lo toglierebbe dai conteggi dei FATTURATI.
-- ⭐ Non serve nessun filtro sullo stadio: la classe TRATTENUTA vuole
--   NON_EMESSA + APPROVATA, quindi su FATTURATA non puo' accendersi.
SELECT is(
  (SELECT count(*)::int
     FROM vendite.vw_dash_competenza_gruppi g
    WHERE g.stadio <> 'DA_EMETTERE' AND g.emissione_blocco_reason IS NOT NULL),
  0,
  '15-quinquies. il verdetto e'' spento fuori da DA_EMETTERE: un documento gia'' fatturato non e'' «trattenuto»'
);

-- ============================================================
-- 15-sexies) ⭐ V-1: il lotto del TENTATIVO esce con il suo STATO
-- ============================================================
-- ⛔ Domanda di Tid: «la colonna mostra il lotto anche se e' annullato». Il
--   dato non si toglie — e' l'unica traccia che spieghi perche' il documento
--   e' tornato disponibile — ma va detto SE quel tentativo conta ancora.
-- ⚠️ `ultimo_lotto_pre_fiscale` e' il flag su cui il frontend spegne il GESTO:
--   testo si', pulsante no.
-- ⚠️ Sta PRIMA dell'annullamento del 15-quater, e non e' un caso: la
--   transizione ANNULLATA -> DRAFT non esiste (guard di stato), quindi i casi
--   «lotto vivo» vanno tutti prima. L'ordine di questo blocco e' portante.
SELECT results_eq(
  $$ SELECT g.ultimo_lotto_id = (SELECT id FROM tmp_dc_lotto_vivo),
            g.ultimo_lotto_stato::text,
            g.ultimo_lotto_pre_fiscale
       FROM vendite.vw_dash_competenza_gruppi g, tmp_dc_trat t
      WHERE g.gruppo_key = t.gruppo_key AND g.stadio = t.stadio $$,
  $$ VALUES (true, 'DRAFT', true) $$,
  '15-sexies. il lotto del tentativo esce con identita'' e STATO: si sa se conta ancora'
);

-- ⭐ IL VERSO OPPOSTO. Annullato il lotto, il documento torna fatturabile: e'
--   il caso in cui `ultimo_esito` (rimasto COMPLETED) non cambia di una virgola
--   e il verdetto invece si ribalta.
UPDATE vendite.fatturazione_lotti
   SET stato_doc_fiscale_id = (SELECT s.id FROM config.stati_doc_fiscale s
                                WHERE s.codice_interno = 'ANNULLATA')
 WHERE id = (SELECT id FROM tmp_dc_lotto_vivo);

SELECT ok(
  (SELECT g.emissione_blocco_reason IS NULL
     FROM vendite.vw_dash_competenza_gruppi g, tmp_dc_trat t
    WHERE g.gruppo_key = t.gruppo_key AND g.stadio = t.stadio),
  '15-quater. annullato il lotto la riga torna libera: il verdetto e'' lo STATO, non l''esito'
);

-- ============================================================
-- 15-septies) ⭐ E il contrario: annullato, il tentativo NON conta piu'
-- ============================================================
-- ⛔ Col solo 15-sexies passerebbe anche una vista che dice sempre «in corso»:
--   e' il caso del collaudo, dove tre righe mostravano un lotto ANNULLATO come
--   se fosse ancora vivo.
-- ⚠️ Il lotto e' gia' annullato dal 15-quater: non si ri-annulla e soprattutto
--   non si torna indietro — la transizione ANNULLATA -> DRAFT non esiste.
SELECT results_eq(
  $$ SELECT g.ultimo_lotto_stato::text, g.ultimo_lotto_pre_fiscale,
            g.ultimo_lotto_codice IS NOT NULL
       FROM vendite.vw_dash_competenza_gruppi g, tmp_dc_trat t
      WHERE g.gruppo_key = t.gruppo_key AND g.stadio = t.stadio $$,
  $$ VALUES ('ANNULLATA', false, true) $$,
  '15-septies. annullato: pre_fiscale falso (il gesto si spegne) ma il codice RESTA (la traccia non si perde)'
);

-- ============================================================
-- 13) SENTINELLA C1/reset (DL-5): il reset della fattura di A4 col verbo
--     vero, vendite.fn_cleanup_fatture_by_ids (solo UPDATE sull'attivita'
--     fatturabile, mai DELETE+reinsert). data_insert deve restare
--     INVARIATA -> il flag ritardo non cambia.
-- ⚠️ ATTESA CAMBIATA (E-4, rev 2026-10-25): lo sgancio scritto a mano (UPDATE
--   con la GUC) lasciava la riga di commessa EMESSA, e lo stadio tornava
--   EMESSA_NON_FATTURATA. Il verbo vero libera anche la riga di commessa
--   (RD-4: torna NON_EMESSA, vendite.fn_libera_attivita_fatturabili): lo
--   stadio torna DA_EMETTERE, con la data di emissione e il ritardo
--   dell'attivita' fatturabile sopravvissuta.
-- ⚠️ In coda, prima del 16, e non piu' fra il 12 e il 14: A4 tornata
--   DA_EMETTERE entrerebbe nei gruppi DA_EMETTERE della commessa che i test
--   15..15-septies leggono come il solo gruppo sourceless.
-- ============================================================
CREATE TEMP TABLE tmp_dc_af_before AS
SELECT af.id, af.data_insert
  FROM vendite.attivita_fatturabili af
 WHERE af.commessa_attivita_id = (SELECT attivita_id FROM tmp_dc_att WHERE slot = 'A4_FATTURATA');

CREATE TEMP TABLE tmp_dc_reset AS
SELECT * FROM vendite.fn_cleanup_fatture_by_ids(ARRAY[(SELECT id FROM tmp_dc_fattura)], NULL);

SELECT ok(
  (SELECT af.data_insert = b.data_insert AND af.fattura_riga_id IS NULL
     FROM vendite.attivita_fatturabili af, tmp_dc_af_before b
    WHERE af.id = b.id)
  AND
  (SELECT v.stadio = 'DA_EMETTERE' AND v.emessa_in_ritardo = true
      AND v.data_emissione = TIMESTAMPTZ '2080-03-15 10:00:00+00'
     FROM vendite.vw_dash_competenza_attivita v
    WHERE v.commessa_attivita_id = (SELECT attivita_id FROM tmp_dc_att WHERE slot = 'A4_FATTURATA')),
  '13. Sentinella reset (DL-5): data_insert INVARIATA dopo il reset vero, stadio torna DA_EMETTERE, ritardo conservato'
);

-- ============================================================
-- 16) FAIL-CLOSED: GUC vuota -> 0 righe (dettaglio e mensile)
-- ============================================================
SELECT set_config('app.current_user_id', '', true);

SELECT ok(
  (SELECT count(*) = 0 FROM vendite.vw_dash_competenza_attivita v
    WHERE v.commessa_id = (SELECT id FROM tmp_dc_commessa))
  AND
  (SELECT count(*) = 0 FROM vendite.vw_dash_competenza_mensile m
    WHERE m.competenza_mese = DATE '2080-01-01'),
  '16. Fail-closed: senza GUC operatore le viste Lente 1 non espongono righe'
);

SELECT * FROM finish();
ROLLBACK;
