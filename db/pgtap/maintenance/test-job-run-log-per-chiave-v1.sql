-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture scrive su dbops.processi e su
--   maintenance.job_run_log, che a runtime scrivono solo i job e le funzioni
--   del giornale, e toglie nella transazione il CHECK che vieta le righe
--   senza processo per costruire una riga storica.
--
-- Test: il giornale delle corse si legge per chiave
--   maintenance.job_run_log (indici), maintenance.vw_job_run_da_guardare e
--   maintenance.vw_job_run_da_superuser (l'ultima corsa per chiave)
-- ChangeSet: 20261122-20, -21, -22 · Brief: brief-db-giornale-corse-indici §6
--
-- Elenco test (plan 8):
--  1-4) ✅ i quattro indici esistono con la loro definizione (colonne,
--       ordine, predicato del parziale)
--  5) ⭐ vw_job_run_da_guardare vede TUTTI i job della fixture: la discesa
--     ricorsiva sui jobname distinti non si ferma al primo
--  6) ⭐ vw_job_run_da_guardare: l'ultima corsa VERA salta la corsa saltata
--     che la segue (la riga della vista e' la fallita)
--  7) ⭐ vw_job_run_da_superuser: per la chiave K vince la riga SENZA processo
--     con jobname K, se e' la piu' recente (il ramo storico della chiave
--     COALESCE(processo_codice, jobname))
--  8) ⭐ vw_job_run_da_superuser: una corsa piu' recente col processo K, di un
--     ruolo non superuser, toglie K dalla vista (i due rami si confrontano)
--
-- ⚠️ La riga senza processo si COSTRUISCE: chk_job_run_log_processo_dichiarato
--   la vieta a ogni corsa nuova, e nel giornale ci sono solo righe storiche.
--   Il CHECK si toglie dentro la transazione, che finisce in ROLLBACK.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

-- ── 1-4: gli indici ──────────────────────────────────────────
SELECT is(
    (SELECT pg_get_indexdef(i.indexrelid) FROM pg_index i
      WHERE i.indexrelid = to_regclass('maintenance.ix_job_run_log_jobname_started_at')),
    'CREATE INDEX ix_job_run_log_jobname_started_at ON maintenance.job_run_log USING btree (jobname, started_at DESC, id DESC)',
    'ix_job_run_log_jobname_started_at: le corse di un job, dalla piu'' recente'
);

SELECT is(
    (SELECT pg_get_indexdef(i.indexrelid) FROM pg_index i
      WHERE i.indexrelid = to_regclass('maintenance.ix_job_run_log_processo_codice_started_at')),
    'CREATE INDEX ix_job_run_log_processo_codice_started_at ON maintenance.job_run_log USING btree (processo_codice, started_at DESC, id DESC)',
    'ix_job_run_log_processo_codice_started_at: le corse di un processo, dalla piu'' recente (copre la FK)'
);

SELECT is(
    (SELECT pg_get_indexdef(i.indexrelid) FROM pg_index i
      WHERE i.indexrelid = to_regclass('maintenance.ix_job_run_log_started_at')),
    'CREATE INDEX ix_job_run_log_started_at ON maintenance.job_run_log USING btree (started_at DESC, id DESC)',
    'ix_job_run_log_started_at: il giornale per recenza'
);

SELECT is(
    (SELECT pg_get_indexdef(i.indexrelid) FROM pg_index i
      WHERE i.indexrelid = to_regclass('maintenance.ix_job_run_log_jobname_senza_processo')),
    'CREATE INDEX ix_job_run_log_jobname_senza_processo ON maintenance.job_run_log USING btree (jobname, started_at DESC, id DESC) WHERE (processo_codice IS NULL)',
    'ix_job_run_log_jobname_senza_processo: le sole righe senza processo'
);

-- ── Fixture ─────────────────────────────────────────────────
INSERT INTO dbops.processi (id, codice, descrizione, classe, canale,
                            jobname_pgagent, tolleranza_minuti, segno_di_vita,
                            acceso_in_sviluppo, acceso_in_produzione, spegnibile, causa_fallimento, accendibile_in_produzione)
VALUES (9982, 'PGTAP-PER-CHIAVE', 'prova giornale per chiave', 'MANUTENZIONE', 'COMMAND', NULL, 30, 'GIORNALE', true, true, true, 'PROGRAMMA', true);

ALTER TABLE maintenance.job_run_log DROP CONSTRAINT chk_job_run_log_processo_dichiarato;

-- Tre job, tutti con l'ultima corsa vera fallita; il secondo ha dopo la
-- fallita una corsa saltata.
INSERT INTO maintenance.job_run_log
    (jobname, processo_codice, ruolo_sessione, started_at, ended_at, ok, saltata, message)
VALUES
    ('PGTAP-PER-CHIAVE-A', 'PGTAP-PER-CHIAVE', 'zeroerp_owner', now() - interval '3 hours', now() - interval '3 hours', false, false, 'a'),
    ('PGTAP-PER-CHIAVE-B', 'PGTAP-PER-CHIAVE', 'zeroerp_owner', now() - interval '3 hours', now() - interval '3 hours', false, false, 'b fallita'),
    ('PGTAP-PER-CHIAVE-B', 'PGTAP-PER-CHIAVE', 'zeroerp_owner', now() - interval '2 hours', now() - interval '2 hours', NULL,  true,  'b saltata'),
    ('PGTAP-PER-CHIAVE-C', 'PGTAP-PER-CHIAVE', 'zeroerp_owner', now() - interval '3 hours', now() - interval '3 hours', false, false, 'c');

-- La chiave PGTAP-PER-CHIAVE: una corsa col processo (non superuser) e,
-- piu' recente, una riga storica senza processo con jobname uguale alla
-- chiave, di un superuser.
INSERT INTO maintenance.job_run_log
    (jobname, processo_codice, ruolo_sessione, started_at, ended_at, ok, saltata, message)
SELECT 'PGTAP-PER-CHIAVE', NULL, r.rolname, now() - interval '1 hour', now() - interval '1 hour', true, false, 'storica'
  FROM pg_roles r
 WHERE r.rolsuper
 ORDER BY r.rolname
 LIMIT 1;

-- ── 5-6: vw_job_run_da_guardare ──────────────────────────────
SELECT is(
    (SELECT count(*)::integer FROM maintenance.vw_job_run_da_guardare
      WHERE jobname IN ('PGTAP-PER-CHIAVE-A', 'PGTAP-PER-CHIAVE-B', 'PGTAP-PER-CHIAVE-C')),
    3,
    'vw_job_run_da_guardare vede tutti e tre i job: la discesa sui jobname distinti non si ferma'
);

SELECT is(
    (SELECT message FROM maintenance.vw_job_run_da_guardare
      WHERE jobname = 'PGTAP-PER-CHIAVE-B'),
    'b fallita',
    'vw_job_run_da_guardare: l''ultima corsa vera salta la corsa saltata che la segue'
);

-- ── 7-8: vw_job_run_da_superuser ─────────────────────────────
SELECT is(
    (SELECT count(*)::integer FROM maintenance.vw_job_run_da_superuser
      WHERE processo_codice = 'PGTAP-PER-CHIAVE'
        AND jobname = 'PGTAP-PER-CHIAVE'),
    1,
    'vw_job_run_da_superuser: per la chiave vince la riga storica senza processo, la piu'' recente'
);

INSERT INTO maintenance.job_run_log
    (jobname, processo_codice, ruolo_sessione, started_at, ended_at, ok, saltata, message)
VALUES
    ('PGTAP-PER-CHIAVE-A', 'PGTAP-PER-CHIAVE', 'zeroerp_owner', now() - interval '10 minutes', now() - interval '10 minutes', true, false, 'a recente');

SELECT is(
    (SELECT count(*)::integer FROM maintenance.vw_job_run_da_superuser
      WHERE processo_codice = 'PGTAP-PER-CHIAVE'),
    0,
    'vw_job_run_da_superuser: la corsa piu'' recente col processo, non superuser, toglie la chiave'
);

SELECT * FROM finish();

ROLLBACK;
