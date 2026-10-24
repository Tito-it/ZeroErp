-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: l'installazione PRODUZIONE si COSTRUISCE riscrivendo
--   la riga di dbops.installazione, che il guard di immutabilita' protegge
--   anche dal proprietario: serve disattivare il trigger (DDL, solo il
--   proprietario), in transazione, annullato col ROLLBACK. Stesso metodo di
--   dbops/test-installazione-ambiente-v1 per l'ambiente non dichiarato.
--
-- Il divieto di accendere a mano in PRODUZIONE un processo non accendibile
-- (smoke_notturno), provato sul DATO e non solo sui valori: il guard della
-- scelta a mano, la riga accesa scritta prima, la sveglia e il panorama.
--   Brief: brief-db-processi-accensione-per-ambiente (§6.6, R-BE-5)
--   changeSet 20261018-10 (accendibile_in_produzione), -11 (il predicato),
--   -12 (la regola ignora la riga non ammessa), -13 (il guard); processi.csv.
--   Il predicato e la regola sui valori, e il catalogo: dbops/test-processi-accensione-v1.
--
-- ⚠️ La CI e' SVILUPPO e l'ambiente e' immutabile: qui lo si cambia DENTRO la
--   transazione del test, a trigger spento, e il ROLLBACK lo rimette. L'ALTER
--   TABLE tiene un lock esclusivo su dbops.installazione fino al ROLLBACK.
--
-- Elenco test (plan 12):
--   in SVILUPPO
--    1) accendere a mano smoke_notturno e' ammesso
--   in PRODUZIONE (costruita)
--    2) l'ambiente costruito e' PRODUZIONE
--    3) ⭐ la riga accesa scritta in SVILUPPO non accende: lo stato e' spento
--    4) ... e la sveglia dice false
--    5) ... e il panorama dice SPENTO, non da guardare
--    6) riaccendere smoke_notturno -> E_PROCESSO_NON_ACCENDIBILE_IN_PRODUZIONE
--    7) riscrivere il solo motivo della riga accesa -> stesso rifiuto
--    8) spegnerlo a mano e' ammesso
--    9) rimetterlo al default e' ammesso: spento, il default di produzione
--   10) un processo accendibile, spento di default in produzione
--       (run_fatturazione_batch), si accende a mano
--   con l'ambiente non dichiarato (costruito)
--   11) accendere smoke_notturno -> E_CONFIG_MANCANTE (il divieto non sa
--       decidere, e lo dice il lettore che decide)
--   12) spegnerlo e' ammesso: il divieto riguarda solo l'accensione
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(12);

-- Il CODICE dell'errore viaggia nel canale CONSTRAINT_NAME dell'eccezione
-- P0001 (fn_log_and_raise_error): si pinna il codice, non la frase.
CREATE OR REPLACE FUNCTION pg_temp.codice_errore(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME;
    RETURN v_c;
END $$;

-- Una scelta a mano gia' presente su questa macchina non deve falsare i test:
--   si parte senza (tutto si annulla col ROLLBACK).
DELETE FROM dbops.processi_accensione a
 USING dbops.processi p
 WHERE p.id = a.processo_id AND p.codice IN ('smoke_notturno', 'run_fatturazione_batch');

SELECT set_config('app.jwt_user', 'pgtap.accensione.produzione', true);

-- ============================================================
-- In SVILUPPO
-- ============================================================
-- ⚠️ Il file parte da un'installazione SVILUPPO (la CI, lo scratch, dbdev).
--   L'ambiente si dichiara SVILUPPO qui sotto, a trigger spento, perche' il
--   test 1 non dipenda dalla macchina.
ALTER TABLE dbops.installazione DISABLE TRIGGER trg_installazione_a05_guard_immutabile_upd_dlt;
DELETE FROM dbops.installazione;
INSERT INTO dbops.installazione (ambiente) VALUES ('SVILUPPO');
ALTER TABLE dbops.installazione ENABLE TRIGGER trg_installazione_a05_guard_immutabile_upd_dlt;

SELECT is(dbops.fn_imposta_accensione_processo('smoke_notturno', true, 'pgTAP: acceso in sviluppo'),
          true, '1. in SVILUPPO accendere a mano smoke_notturno e'' ammesso');

-- ============================================================
-- In PRODUZIONE, costruita: la riga accesa di prima resta li'
-- ============================================================
ALTER TABLE dbops.installazione DISABLE TRIGGER trg_installazione_a05_guard_immutabile_upd_dlt;
UPDATE dbops.installazione SET ambiente = 'PRODUZIONE';
ALTER TABLE dbops.installazione ENABLE TRIGGER trg_installazione_a05_guard_immutabile_upd_dlt;

SELECT is(script.fn_ambiente_installazione(), 'PRODUZIONE',
          '2. l''ambiente costruito e'' PRODUZIONE');

SELECT is(dbops.fn_processo_acceso_dichiarato('smoke_notturno'), false,
          '3. la riga accesa scritta prima non accende: vale il default di produzione, spento');

SELECT is(maintenance.fn_sveglia_accesa('smoke_notturno'), false,
          '4. ... e la sveglia di smoke_notturno e'' spenta');

SELECT is(
    (SELECT format('%s|%s|%s', v.stato, v.da_guardare, v.acceso)
       FROM dbops.vw_processi_programmazione v
      WHERE v.processo_codice = 'smoke_notturno'),
    'SPENTO|f|f',
    '5. ... e il panorama dice SPENTO, non da guardare');

SELECT is(pg_temp.codice_errore($$SELECT dbops.fn_imposta_accensione_processo('smoke_notturno', true, 'pgTAP: riaccendo in produzione')$$),
          'E_PROCESSO_NON_ACCENDIBILE_IN_PRODUZIONE',
          '6. riaccendere smoke_notturno in PRODUZIONE: E_PROCESSO_NON_ACCENDIBILE_IN_PRODUZIONE');

SELECT is(pg_temp.codice_errore($$
              UPDATE dbops.processi_accensione a
                 SET motivo = 'pgTAP: ritocco il motivo'
                FROM dbops.processi p
               WHERE p.id = a.processo_id AND p.codice = 'smoke_notturno'$$),
          'E_PROCESSO_NON_ACCENDIBILE_IN_PRODUZIONE',
          '7. la riga accesa non si riscrive accesa, nemmeno ritoccando il solo motivo');

SELECT is(dbops.fn_imposta_accensione_processo('smoke_notturno', false, 'pgTAP: spento in produzione'),
          false, '8. spegnerlo a mano e'' ammesso');

SELECT is(dbops.fn_imposta_accensione_processo('smoke_notturno', NULL, 'pgTAP: default in produzione'),
          false, '9. rimetterlo al default e'' ammesso: spento, il default di produzione');

SELECT is(dbops.fn_imposta_accensione_processo('run_fatturazione_batch', true, 'pgTAP: pronto per SDI'),
          true, '10. un accendibile spento di default in produzione si accende a mano');

-- ============================================================
-- Con l'ambiente non dichiarato, costruito
-- ============================================================
ALTER TABLE dbops.installazione DISABLE TRIGGER trg_installazione_a05_guard_immutabile_upd_dlt;
DELETE FROM dbops.installazione;
ALTER TABLE dbops.installazione ENABLE TRIGGER trg_installazione_a05_guard_immutabile_upd_dlt;

SELECT is(pg_temp.codice_errore($$SELECT dbops.fn_imposta_accensione_processo('smoke_notturno', true, 'pgTAP: accendo senza ambiente')$$),
          'E_CONFIG_MANCANTE',
          '11. ambiente non dichiarato: accendere un non accendibile non si decide, E_CONFIG_MANCANTE');

SELECT is(dbops.fn_imposta_accensione_processo('smoke_notturno', false, 'pgTAP: spento senza ambiente'),
          false, '12. spegnerlo e'' ammesso anche senza ambiente: il divieto riguarda solo l''accensione');

SELECT * FROM finish();

ROLLBACK;
