-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: il ramo PRODUZIONE si COSTRUISCE riscrivendo la riga di
--   dbops.installazione, che il guard di immutabilita' protegge anche dal
--   proprietario: serve disattivare il trigger (DDL, solo il proprietario), in
--   transazione, annullato col ROLLBACK. Stesso metodo di
--   dbops/test-processi-accensione-produzione-v1.
--
-- Le etichette di prova e la loro porta (R-4, 2b-3):
--   dbops.credenziali_di_prova, dbops.soggetti_di_prova   (20261018-55, -56)
--   dbops.fn_dati_di_sviluppo_ammessi_su_valori           (20261018-57)
--   dbops.trgfn_etichette_di_prova_guard e i suoi trigger (20261018-58, -59)
--   la postura dell'app (90_end/20261018-61, loop 20260205-41, provisioning)
--   il presidio dbops.vw_radici_di_prova_in_produzione    (20261018-62)
--   il rifiuto del verbo anagrafiche.fn_provisiona_dati_di_sviluppo (20261018-60)
--   Brief: brief-db-processi-accensione-per-ambiente (R-4, §5.5).
--
-- ⭐ Le etichette si scrivono qui a mano da owner apposta: si prova il GUARD
--   della tabella, non il verbo (che ha il suo file).
--
-- Elenco test (plan 16):
--   la regola, sui valori
--    1) SVILUPPO: ammessi
--    2) PRODUZIONE: no
--    3) NULL resta NULL
--   la postura dell'app
--    4) zeroerp_app legge le due tabelle
--    5) ... e non le scrive (INSERT, UPDATE, DELETE)
--   il guard, in SVILUPPO
--    6) un'etichetta di soggetto nasce
--    7) ... e una di credenziale
--    8) UPDATE: E_ETICHETTA_DI_PROVA_IMMUTABILE
--    9) DELETE: E_ETICHETTA_DI_PROVA_IMMUTABILE
--   10) TRUNCATE: E_ETICHETTA_DI_PROVA_IMMUTABILE
--   11) il presidio, in SVILUPPO, e' vuoto
--   in PRODUZIONE (costruita)
--   12) un'etichetta nuova: E_DATI_DI_SVILUPPO_IN_PRODUZIONE
--   13) il presidio vede le due etichette nate prima
--   14) il verbo non parte: E_DATI_DI_SVILUPPO_IN_PRODUZIONE
--   con l'ambiente non dichiarato (costruito)
--   15) un'etichetta nuova: E_CONFIG_MANCANTE (lo dice il lettore)
--   16) il presidio e' vuoto (lo dice vw_ambiente_non_dichiarato)
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(16);


-- ============================================================
-- La regola, sui valori
-- ============================================================
SELECT is(dbops.fn_dati_di_sviluppo_ammessi_su_valori('SVILUPPO'), true, '1. SVILUPPO: ammessi');
SELECT is(dbops.fn_dati_di_sviluppo_ammessi_su_valori('PRODUZIONE'), false, '2. PRODUZIONE: no');
SELECT is(dbops.fn_dati_di_sviluppo_ammessi_su_valori(NULL), NULL::boolean, '3. NULL resta NULL');

-- ============================================================
-- La postura dell'app
-- ============================================================
SELECT ok(has_table_privilege('zeroerp_app', 'dbops.credenziali_di_prova', 'SELECT')
          AND has_table_privilege('zeroerp_app', 'dbops.soggetti_di_prova', 'SELECT'),
          '4. zeroerp_app legge le due tabelle');

SELECT is(
    (SELECT count(*)::int
       FROM unnest(ARRAY['dbops.credenziali_di_prova', 'dbops.soggetti_di_prova']) AS t,
            unnest(ARRAY['INSERT', 'UPDATE', 'DELETE']) AS p
      WHERE has_table_privilege('zeroerp_app', t, p)),
    0,
    '5. ... e non le scrive (INSERT, UPDATE, DELETE)');

-- ============================================================
-- Il guard, in SVILUPPO
-- ============================================================
-- ⚠️ L'ambiente si dichiara SVILUPPO qui, a trigger spento, perche' il file non
--   dipenda dalla macchina.
ALTER TABLE dbops.installazione DISABLE TRIGGER trg_installazione_a05_guard_immutabile_upd_dlt;
DELETE FROM dbops.installazione;
INSERT INTO dbops.installazione (ambiente) VALUES ('SVILUPPO');
ALTER TABLE dbops.installazione ENABLE TRIGGER trg_installazione_a05_guard_immutabile_upd_dlt;

CREATE TEMP TABLE t_s AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('Etichetta pgTAP') AS soggetto_id,
       dbops.fn_pgtap_crea_soggetto_pg('Etichetta pgTAP 2') AS soggetto_id2,
       (SELECT o.auth_user_id FROM dbops.fn_pgtap_crea_operatore_umano('Etichetta pgTAP', false) o) AS auth_user_id;

SELECT lives_ok(
    $$INSERT INTO dbops.soggetti_di_prova (soggetto_id, chiave)
      SELECT soggetto_id, 'PGTAP-ETICHETTA-1' FROM t_s$$,
    '6. un''etichetta di soggetto nasce');

SELECT lives_ok(
    $$INSERT INTO dbops.credenziali_di_prova (auth_user_id, chiave)
      SELECT auth_user_id, 'pgtap.etichetta' FROM t_s$$,
    '7. ... e una di credenziale');

SELECT is(
    dbops.fn_pgtap_codice_errore($$UPDATE dbops.soggetti_di_prova SET chiave = 'PGTAP-ALTRA' WHERE chiave = 'PGTAP-ETICHETTA-1'$$),
    'E_ETICHETTA_DI_PROVA_IMMUTABILE',
    '8. UPDATE: E_ETICHETTA_DI_PROVA_IMMUTABILE');

SELECT is(
    dbops.fn_pgtap_codice_errore($$DELETE FROM dbops.credenziali_di_prova WHERE chiave = 'pgtap.etichetta'$$),
    'E_ETICHETTA_DI_PROVA_IMMUTABILE',
    '9. DELETE: E_ETICHETTA_DI_PROVA_IMMUTABILE');

SELECT is(
    dbops.fn_pgtap_codice_errore($$TRUNCATE dbops.soggetti_di_prova$$),
    'E_ETICHETTA_DI_PROVA_IMMUTABILE',
    '10. TRUNCATE: E_ETICHETTA_DI_PROVA_IMMUTABILE');

SELECT is((SELECT count(*)::int FROM dbops.vw_radici_di_prova_in_produzione), 0,
          '11. il presidio, in SVILUPPO, e'' vuoto');

-- ============================================================
-- In PRODUZIONE, costruita
-- ============================================================
ALTER TABLE dbops.installazione DISABLE TRIGGER trg_installazione_a05_guard_immutabile_upd_dlt;
UPDATE dbops.installazione SET ambiente = 'PRODUZIONE';
ALTER TABLE dbops.installazione ENABLE TRIGGER trg_installazione_a05_guard_immutabile_upd_dlt;

SELECT is(
    dbops.fn_pgtap_codice_errore($$INSERT INTO dbops.soggetti_di_prova (soggetto_id, chiave)
                            SELECT soggetto_id2, 'PGTAP-ETICHETTA-2' FROM t_s$$),
    'E_DATI_DI_SVILUPPO_IN_PRODUZIONE',
    '12. in PRODUZIONE un''etichetta nuova: E_DATI_DI_SVILUPPO_IN_PRODUZIONE');

SELECT is(
    (SELECT string_agg(v.tipo || ':' || v.chiave, ',' ORDER BY v.tipo)
       FROM dbops.vw_radici_di_prova_in_produzione v
      WHERE v.chiave IN ('PGTAP-ETICHETTA-1', 'pgtap.etichetta')),
    'CREDENZIALE:pgtap.etichetta,SOGGETTO:PGTAP-ETICHETTA-1',
    '13. il presidio vede le due etichette nate prima');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT * FROM anagrafiche.fn_provisiona_dati_di_sviluppo()$$),
    'E_DATI_DI_SVILUPPO_IN_PRODUZIONE',
    '14. il verbo non parte: E_DATI_DI_SVILUPPO_IN_PRODUZIONE');

-- ============================================================
-- Con l'ambiente non dichiarato, costruito
-- ============================================================
ALTER TABLE dbops.installazione DISABLE TRIGGER trg_installazione_a05_guard_immutabile_upd_dlt;
DELETE FROM dbops.installazione;
ALTER TABLE dbops.installazione ENABLE TRIGGER trg_installazione_a05_guard_immutabile_upd_dlt;

SELECT is(
    dbops.fn_pgtap_codice_errore($$INSERT INTO dbops.soggetti_di_prova (soggetto_id, chiave)
                            SELECT soggetto_id2, 'PGTAP-ETICHETTA-3' FROM t_s$$),
    'E_CONFIG_MANCANTE',
    '15. ambiente non dichiarato: E_CONFIG_MANCANTE, dal lettore');

SELECT is((SELECT count(*)::int FROM dbops.vw_radici_di_prova_in_produzione), 0,
          '16. il presidio e'' vuoto (lo dice vw_ambiente_non_dichiarato)');

SELECT * FROM finish();

ROLLBACK;
