-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: viste Lente 1 Competenza (20260706-09..11 + indice -14):
--       vw_dash_competenza_attivita (dettaglio grana attivita', stadi funnel,
--       recuperi tardivi da attivita_fatturabili.data_insert),
--       vw_dash_competenza_mensile (aggregata formato lungo),
--       vw_dash_competenza_errori (task run ERRORE vivi + fatture critical).
--       Brief: brief-db-fatturazione-due-lenti §4 e §7.
--       Fixture: commessa (emittente A) con 4 attivita' 2080-01 nei 4 stadi
--       (10/20/30/40) + 1 void ANNULLATA; fattura BOZZA collegata; lotto
--       2080-04 con task run in ERRORE.
--
-- Indice test (0..14):
--   0)  Precondizioni (refs: BA, articoli, stati, registro, emittente A)
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
--   13) SENTINELLA C1/reset (DL-5): dopo unlink stile fn_cleanup_fatture_by_ids
--       data_insert INVARIATA, stadio torna EMESSA_NON_FATTURATA, ritardo resta
--   14) FAIL-CLOSED: GUC vuota -> 0 righe in dettaglio e mensile
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

SELECT plan(15);

-- ============================================================
-- 0) Riferimenti minimi
-- ============================================================
CREATE TEMP TABLE tmp_dc_refs AS
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
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE AND a.is_composito = FALSE ORDER BY a.id LIMIT 1) AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE
    ORDER BY u.id LIMIT 1) AS uom_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE
    ORDER BY t.id LIMIT 1) AS tipo_doc_fiscale_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT sc.id FROM vendite.stati_commessa sc
    WHERE sc.attivo IS TRUE AND sc.codice_interno <> 'ANNULLATA'
    ORDER BY sc.id LIMIT 1) AS stato_commessa_id,
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef WHERE ef.attivo IS TRUE
    ORDER BY ef.id LIMIT 1) AS emittente_fiscale_id,
  (SELECT ef.soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.attivo IS TRUE ORDER BY ef.id LIMIT 1) AS ef_a_sr,
  (SELECT s.id FROM config.sorgenti s
    WHERE s.codice_interno = 'PREVENTIVO' AND s.attivo IS TRUE LIMIT 1) AS sorg_preventivo_id,
  (SELECT r.id FROM vendite.registri_fatturazione r WHERE r.attivo IS TRUE
    ORDER BY r.id LIMIT 1) AS registro_id,
  (SELECT s.id FROM config.stati_doc_fiscale s WHERE s.attivo IS TRUE
    ORDER BY COALESCE(s.ordine, 32767), s.id LIMIT 1) AS stato_fiscale_id,
  (SELECT s.codice_interno FROM config.stati_doc_fiscale s WHERE s.attivo IS TRUE
    ORDER BY COALESCE(s.ordine, 32767), s.id LIMIT 1) AS stato_fiscale_ci;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL AND articolo_id IS NOT NULL
      AND uom_id IS NOT NULL AND tipo_doc_fiscale_id IS NOT NULL
      AND stato_commessa_id IS NOT NULL AND ef_a_sr IS NOT NULL
      AND registro_id IS NOT NULL AND stato_fiscale_id IS NOT NULL
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
CREATE TEMP TABLE tmp_dc_op AS
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
  (SELECT user_id IS NOT NULL FROM tmp_dc_op),
  '2. Trovato un operatore OPERATORE non-super per lo scope'
);

SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on';
DELETE FROM config.user_emittenti_fiscali
 WHERE auth_user_id = (SELECT user_id FROM tmp_dc_op);
SET LOCAL zeroerp.allow_user_emittente_delete_override = '';

INSERT INTO config.user_emittenti_fiscali (auth_user_id, emittente_fiscale_id, meta)
SELECT o.user_id, r.emittente_fiscale_id,
       '{"test_scope":"pgtap_dash_competenza"}'::jsonb
  FROM tmp_dc_op o, tmp_dc_refs r
 WHERE o.user_id IS NOT NULL;

SELECT set_config('app.current_user_id',
    (SELECT user_id::text FROM tmp_dc_op), true);

-- ============================================================
-- Fixture: commessa (emittente A) + 4 attivita' 2080-01 (una per stadio)
-- + 1 void ANNULLATA. Valori 10/20/30/40 (+999 void).
-- ============================================================
CREATE TEMP TABLE tmp_dc_commessa AS
WITH ins AS (
  INSERT INTO vendite.commesse (codice, billing_account_id, utility_id,
                                emittente_soggetto_ruolo_id, stato_commessa_id)
  SELECT 'PGTAP-DC-CMD-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.billing_account_id, r.utility_id, r.ef_a_sr, r.stato_commessa_id
    FROM tmp_dc_refs r
  RETURNING id)
SELECT id FROM ins;

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
         'BOZZA', 'NON_EMESSA', NULL, NULL
    FROM tmp_dc_refs r
  RETURNING id)
INSERT INTO tmp_dc_att SELECT 'A1_DA_APPROVARE', id FROM ins;

WITH ins AS (
  INSERT INTO vendite.commesse_attivita (
    commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
    uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
    tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
    stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
  SELECT (SELECT id FROM tmp_dc_commessa),
         'PGTAP-DC-A2-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.articolo_id, r.istanza_utility_id, DATE '2080-01-01', r.uom_id, 1,
         DATE '2080-01-01', DATE '2080-01-01', DATE '2080-01-31',
         r.tipo_doc_fiscale_id, r.valuta_id, 20.000000, 'FIXED',
         'APPROVATA', 'NON_EMESSA', NULL, NULL
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
         'APPROVATA', 'EMESSA', NULL, NULL
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
         'APPROVATA', 'EMESSA', NULL, NULL
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
         'APPROVATA', 'ANNULLATA', NULL, NULL
    FROM tmp_dc_refs r
  RETURNING id)
INSERT INTO tmp_dc_att SELECT 'A5_VOID', id FROM ins;

-- Fattura BOZZA (senza numero) + riga: destinazione dell'AF di A4.
CREATE TEMP TABLE tmp_dc_fattura AS
WITH ins AS (
  INSERT INTO vendite.fatture (
    registro_id, data, tipo_doc_fiscale_id, stato_doc_fiscale_id,
    emittente_soggetto_ruolo_id, billing_account_id, meta)
  SELECT r.registro_id, DATE '2080-03-15', r.tipo_doc_fiscale_id, r.stato_fiscale_id,
         r.ef_a_sr, r.billing_account_id,
         jsonb_build_object('test_scope','pgtap_dash_competenza')
    FROM tmp_dc_refs r
  RETURNING id)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_dc_fattura_riga AS
WITH ins AS (
  INSERT INTO vendite.fatture_righe (
    fattura_id, riga_nr, descrizione, qta, prezzo_unitario, imponibile_riga)
  SELECT (SELECT id FROM tmp_dc_fattura), 1,
         'PGTAP dash competenza', 1, 40.000000, 40.000000
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
  commessa_id, commessa_attivita_id, data_insert)
SELECT r.articolo_id, r.istanza_utility_id, DATE '2080-01-01', 1,
       DATE '2080-01-01', DATE '2080-01-01', DATE '2080-01-31',
       r.uom_id, r.valuta_id, 30.000000, r.tipo_doc_fiscale_id,
       (SELECT id FROM tmp_dc_commessa),
       (SELECT attivita_id FROM tmp_dc_att WHERE slot = 'A3_EMESSA'),
       TIMESTAMPTZ '2080-01-05 10:00:00+00'
FROM tmp_dc_refs r;

INSERT INTO vendite.attivita_fatturabili (
  articolo_id, istanza_utility_id, data_attivita, quantita,
  competenza_mese, competenza_dal, competenza_al,
  uom_id, valuta_id, prezzo_unitario, tipo_doc_fiscale_id,
  commessa_id, commessa_attivita_id, fattura_riga_id, fatturato, data_insert)
SELECT r.articolo_id, r.istanza_utility_id, DATE '2080-01-01', 1,
       DATE '2080-01-01', DATE '2080-01-01', DATE '2080-01-31',
       r.uom_id, r.valuta_id, 40.000000, r.tipo_doc_fiscale_id,
       (SELECT id FROM tmp_dc_commessa),
       (SELECT attivita_id FROM tmp_dc_att WHERE slot = 'A4_FATTURATA'),
       (SELECT id FROM tmp_dc_fattura_riga), true,
       TIMESTAMPTZ '2080-03-15 10:00:00+00'
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
-- 13) SENTINELLA C1/reset (DL-5): unlink della riga AF stile
--     fn_cleanup_fatture_by_ids (solo UPDATE, mai DELETE+reinsert).
--     data_insert deve restare INVARIATA -> il flag ritardo non cambia.
-- ============================================================
CREATE TEMP TABLE tmp_dc_af_before AS
SELECT af.id, af.data_insert
  FROM vendite.attivita_fatturabili af
 WHERE af.commessa_attivita_id = (SELECT attivita_id FROM tmp_dc_att WHERE slot = 'A4_FATTURATA');

-- Bypass del guard fatturato (stesso GUC usato dal cleanup di produzione).
SELECT set_config('zeroerp.maintenance_reset_lotto_draft', 'on', true);
UPDATE vendite.attivita_fatturabili
   SET fattura_riga_id = NULL, fatturato = false, stato_esecuzione = NULL,
       lock_in_fatturazione = false, lock_batch_id = NULL, data_update = now()
 WHERE id = (SELECT id FROM tmp_dc_af_before);
SELECT set_config('zeroerp.maintenance_reset_lotto_draft', '', true);

SELECT ok(
  (SELECT af.data_insert = b.data_insert
     FROM vendite.attivita_fatturabili af, tmp_dc_af_before b
    WHERE af.id = b.id)
  AND
  (SELECT v.stadio = 'EMESSA_NON_FATTURATA' AND v.emessa_in_ritardo = true
      AND v.data_emissione = TIMESTAMPTZ '2080-03-15 10:00:00+00'
     FROM vendite.vw_dash_competenza_attivita v
    WHERE v.commessa_attivita_id = (SELECT attivita_id FROM tmp_dc_att WHERE slot = 'A4_FATTURATA')),
  '13. Sentinella reset (DL-5): data_insert INVARIATA dopo l''unlink, stadio torna EMESSA_NON_FATTURATA, ritardo conservato'
);

-- ============================================================
-- 14) FAIL-CLOSED: GUC vuota -> 0 righe (dettaglio e mensile)
-- ============================================================
SELECT set_config('app.current_user_id', '', true);

SELECT ok(
  (SELECT count(*) = 0 FROM vendite.vw_dash_competenza_attivita v
    WHERE v.commessa_id = (SELECT id FROM tmp_dc_commessa))
  AND
  (SELECT count(*) = 0 FROM vendite.vw_dash_competenza_mensile m
    WHERE m.competenza_mese = DATE '2080-01-01'),
  '14. Fail-closed: senza GUC operatore le viste Lente 1 non espongono righe'
);

SELECT * FROM finish();
ROLLBACK;
