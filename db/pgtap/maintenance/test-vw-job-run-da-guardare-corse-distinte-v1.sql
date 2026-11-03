-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture scrive su dbops.processi e su
--   maintenance.job_run_log, che a runtime scrivono solo i job e le funzioni
--   del giornale. Il ruolo applicativo ha SELECT e basta.
--
-- Test: il presidio dei job conta le CORSE fallite, non le righe rosse
--   maintenance.vw_job_run_da_guardare.falliti_ultimi_7_giorni
-- ChangeSet: 20261103-60 · Brief: brief-db-revisione-maintenance D10
--
-- Elenco test (plan 2):
--  1) ✅ il job con l'ultima corsa fallita compare nel presidio
--  2) ⭐ una corsa fallita con DUE righe rosse (stesso run_uuid) conta una
--     volta: falliti_ultimi_7_giorni = 2 per due corse, non 3
--
-- ⚠️ Le due righe con lo stesso run_uuid si COSTRUISCONO: e' la forma che
--   lascia maintenance.fn_run_and_log quando il chiamante cattura l'eccezione
--   (la riga aggiornata in transazione + quella scritta fuori transazione), e
--   provocarla davvero richiede il canale dblink.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(2);

INSERT INTO dbops.processi (id, codice, descrizione, classe, canale,
                            jobname_pgagent, tolleranza_minuti, segno_di_vita,
                            acceso_in_sviluppo, acceso_in_produzione, spegnibile, causa_fallimento, accendibile_in_produzione)
VALUES (9994, 'PGTAP-CORSE-DISTINTE', 'prova corse distinte', 'MANUTENZIONE', 'COMMAND', NULL, 30, 'GIORNALE', true, true, true, 'PROGRAMMA', true);

-- Due corse fallite: la prima ha una riga sola, la seconda (l'ultima) due
-- righe con lo stesso run_uuid.
INSERT INTO maintenance.job_run_log
    (jobname, stepname, processo_codice, ruolo_sessione, run_uuid,
     started_at, ended_at, ok, message, error_code, sqlstate)
VALUES
    ('PGTAP-CORSE-DISTINTE', 'step', 'PGTAP-CORSE-DISTINTE', session_user,
     '00000000-0000-7000-8000-00000000d101',
     now() - interval '2 hours', now() - interval '2 hours', false, 'prima', 'XX000', 'XX000'),
    ('PGTAP-CORSE-DISTINTE', 'step', 'PGTAP-CORSE-DISTINTE', session_user,
     '00000000-0000-7000-8000-00000000d102',
     now() - interval '1 hour', now() - interval '1 hour', false, 'seconda, in transazione', 'XX000', 'XX000'),
    ('PGTAP-CORSE-DISTINTE', 'step', 'PGTAP-CORSE-DISTINTE', session_user,
     '00000000-0000-7000-8000-00000000d102',
     now() - interval '1 hour', now() - interval '1 hour', false, 'seconda, fuori transazione', 'XX000', 'XX000');

SELECT ok(
    EXISTS (SELECT 1 FROM maintenance.vw_job_run_da_guardare
             WHERE jobname = 'PGTAP-CORSE-DISTINTE'),
    'Il job con l''ultima corsa fallita compare nel presidio'
);

SELECT is(
    (SELECT falliti_ultimi_7_giorni::integer FROM maintenance.vw_job_run_da_guardare
      WHERE jobname = 'PGTAP-CORSE-DISTINTE'),
    2,
    'Due corse fallite contano due, anche se l''ultima ha lasciato due righe rosse'
);

SELECT * FROM finish();

ROLLBACK;
