-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture scrive su dbops.processi e su
--   maintenance.job_run_log, che a runtime scrivono solo i job e le funzioni
--   del giornale.
--
-- Test: il giornale delle corse si legge per chiave, e ogni corsa ha il suo processo
--   maintenance.job_run_log (indici, processo obbligatorio),
--   maintenance.vw_job_run_corsie (le corsie),
--   maintenance.vw_job_run_da_guardare e maintenance.vw_job_run_da_superuser
--   (l'ultima corsa per chiave)
-- ChangeSet: 20261122-20 … -25, -44, -45 · Brief: brief-db-giornale-corse-indici §6, §8, §11.5
--
-- Elenco test (plan 16):
--  1-4) ✅ i quattro indici di lettura con la loro definizione (colonne, ordine)
--  5) ✅ l'indice parziale delle righe senza processo non c'e' piu'
--  6) ✅ processo_codice e' NOT NULL
--  7) ✅ chk_job_run_log_processo_dichiarato non c'e' piu': lo dice il NOT NULL
--  8) ⭐ una corsa senza processo non entra (23502)
--  9) ⭐ vw_job_run_da_guardare vede TUTTI i job della fixture: la discesa
--     ricorsiva sui jobname distinti non si ferma al primo
-- 10) ⭐ vw_job_run_da_guardare: l'ultima corsa VERA salta la corsa saltata
--     che la segue (la riga della vista e' la fallita)
-- 11) ⭐ vw_job_run_da_superuser vede TUTTI e due i processi la cui ultima
--     corsa col ruolo e' di un superuser: la discesa sui processi non si ferma
-- 12) ⭐ vw_job_run_da_superuser: una corsa piu' recente dello stesso processo,
--     di un ruolo non superuser, toglie il processo dalla vista
-- 13-16) ⭐ La corsia e' la coppia (processo, jobname). Due processi, X e Y,
--     con una corsia dello stesso nome, costruiti apposta: X ha un rosso di
--     dieci giorni fa e nient'altro; Y un rosso di otto giorni fa e un verde
--     di un'ora fa. Con la chiave sul solo nome il verde di Y nasconde X, e
--     nessun rosso cade nei sette giorni: la vista non mostra niente (13 rosso).
--     L'ultimo rosso di Y e' piu' recente di quello di X: con la LATERAL sul
--     solo nome la causa di X si leggerebbe da Y (14 rosso), e i falliti di X
--     conterebbero anche quello di Y (15 rosso).
-- 13) vw_job_run_da_guardare: per quel nome, solo la corsia di X
-- 14) l'ultimo rosso della riga di X e' il rosso di X
-- 15) falliti_ultimi_7_giorni della riga di X conta solo le corse di X
-- 16) vw_job_run_corsie: il nome comune sono due corsie, una per processo
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(16);

-- ── 1-5: gli indici ──────────────────────────────────────────
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
      WHERE i.indexrelid = to_regclass('maintenance.ix_job_run_log_processo_codice_jobname_started_at')),
    'CREATE INDEX ix_job_run_log_processo_codice_jobname_started_at ON maintenance.job_run_log USING btree (processo_codice, jobname, started_at DESC, id DESC)',
    'ix_job_run_log_processo_codice_jobname_started_at: le corsie di un processo, e le corse di ciascuna'
);

SELECT ok(
    to_regclass('maintenance.ix_job_run_log_jobname_senza_processo') IS NULL,
    'ix_job_run_log_jobname_senza_processo non c''e'' piu'': non ci sono righe senza processo'
);

-- ── 6-8: il processo obbligatorio ────────────────────────────
SELECT col_not_null('maintenance', 'job_run_log', 'processo_codice',
    'processo_codice e'' NOT NULL: ogni corsa ha il suo processo');

SELECT is(
    (SELECT count(*)::integer FROM pg_constraint
      WHERE conrelid = 'maintenance.job_run_log'::regclass
        AND conname = 'chk_job_run_log_processo_dichiarato'),
    0,
    'chk_job_run_log_processo_dichiarato non c''e'' piu'': il NOT NULL dice la stessa cosa'
);

SELECT throws_ok(
    $$INSERT INTO maintenance.job_run_log (jobname, processo_codice, started_at, ended_at, ok)
      VALUES ('PGTAP-PER-CHIAVE-MUTA', NULL, now(), now(), true)$$,
    '23502',
    NULL,
    'una corsa senza processo non entra'
);

-- ── Fixture ─────────────────────────────────────────────────
INSERT INTO dbops.processi (id, codice, descrizione, classe, canale,
                            jobname_pgagent, tolleranza_minuti, segno_di_vita,
                            acceso_in_sviluppo, acceso_in_produzione, spegnibile, causa_fallimento, accendibile_in_produzione)
VALUES (9982, 'PGTAP-PER-CHIAVE',   'prova giornale per chiave', 'MANUTENZIONE', 'COMMAND', NULL, 30, 'GIORNALE', true, true, true, 'PROGRAMMA', true),
       (9983, 'PGTAP-PER-CHIAVE-2', 'prova giornale per chiave', 'MANUTENZIONE', 'COMMAND', NULL, 30, 'GIORNALE', true, true, true, 'PROGRAMMA', true);

-- Tre job, tutti con l'ultima corsa vera fallita; il secondo ha dopo la
-- fallita una corsa saltata.
INSERT INTO maintenance.job_run_log
    (jobname, processo_codice, ruolo_sessione, started_at, ended_at, ok, saltata, message)
VALUES
    ('PGTAP-PER-CHIAVE-A', 'PGTAP-PER-CHIAVE', 'zeroerp_owner', now() - interval '3 hours', now() - interval '3 hours', false, false, 'a'),
    ('PGTAP-PER-CHIAVE-B', 'PGTAP-PER-CHIAVE', 'zeroerp_owner', now() - interval '3 hours', now() - interval '3 hours', false, false, 'b fallita'),
    ('PGTAP-PER-CHIAVE-B', 'PGTAP-PER-CHIAVE', 'zeroerp_owner', now() - interval '2 hours', now() - interval '2 hours', NULL,  true,  'b saltata'),
    ('PGTAP-PER-CHIAVE-C', 'PGTAP-PER-CHIAVE', 'zeroerp_owner', now() - interval '3 hours', now() - interval '3 hours', false, false, 'c');

-- Per tutti e due i processi, la corsa col ruolo piu' recente e' di un
-- superuser.
INSERT INTO maintenance.job_run_log
    (jobname, processo_codice, ruolo_sessione, started_at, ended_at, ok, saltata, message)
SELECT p.jobname, p.processo_codice, r.rolname, now() - interval '1 hour', now() - interval '1 hour', true, false, 'da superuser'
  FROM (VALUES ('PGTAP-PER-CHIAVE-A', 'PGTAP-PER-CHIAVE'),
               ('PGTAP-PER-CHIAVE-2', 'PGTAP-PER-CHIAVE-2')) AS p (jobname, processo_codice)
 CROSS JOIN (SELECT rolname FROM pg_roles WHERE rolsuper ORDER BY rolname LIMIT 1) r;

-- ── 9-10: vw_job_run_da_guardare ─────────────────────────────
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

-- ── 11-12: vw_job_run_da_superuser ───────────────────────────
SELECT is(
    (SELECT count(*)::integer FROM maintenance.vw_job_run_da_superuser
      WHERE processo_codice IN ('PGTAP-PER-CHIAVE', 'PGTAP-PER-CHIAVE-2')),
    2,
    'vw_job_run_da_superuser vede tutti e due i processi: la discesa sui processi non si ferma'
);

INSERT INTO maintenance.job_run_log
    (jobname, processo_codice, ruolo_sessione, started_at, ended_at, ok, saltata, message)
VALUES
    ('PGTAP-PER-CHIAVE-C', 'PGTAP-PER-CHIAVE', 'zeroerp_owner', now() - interval '10 minutes', now() - interval '10 minutes', true, false, 'c recente');

SELECT results_eq(
    $$SELECT processo_codice FROM maintenance.vw_job_run_da_superuser
       WHERE processo_codice IN ('PGTAP-PER-CHIAVE', 'PGTAP-PER-CHIAVE-2')$$,
    $$VALUES ('PGTAP-PER-CHIAVE-2'::text)$$,
    'vw_job_run_da_superuser: la corsa piu'' recente del processo, di un non superuser, lo toglie dalla vista'
);

-- ── 13-16: la corsia e' la coppia ───────────────────────────
INSERT INTO dbops.processi (id, codice, descrizione, classe, canale,
                            jobname_pgagent, tolleranza_minuti, segno_di_vita,
                            acceso_in_sviluppo, acceso_in_produzione, spegnibile, causa_fallimento, accendibile_in_produzione)
VALUES (9984, 'PGTAP-CORSIA-X', 'prova corsia per coppia', 'MANUTENZIONE', 'COMMAND', NULL, 30, 'GIORNALE', true, true, true, 'PROGRAMMA', true),
       (9985, 'PGTAP-CORSIA-Y', 'prova corsia per coppia', 'MANUTENZIONE', 'COMMAND', NULL, 30, 'GIORNALE', true, true, true, 'PROGRAMMA', true);

INSERT INTO maintenance.job_run_log
    (jobname, processo_codice, ruolo_sessione, started_at, ended_at, ok, saltata, message, run_uuid)
VALUES
    ('PGTAP-CORSIA-COMUNE', 'PGTAP-CORSIA-X', 'zeroerp_owner', now() - interval '10 days', now() - interval '10 days', false, false, 'x rossa', gen_random_uuid()),
    ('PGTAP-CORSIA-COMUNE', 'PGTAP-CORSIA-Y', 'zeroerp_owner', now() - interval '8 days',  now() - interval '8 days',  false, false, 'y rossa', gen_random_uuid()),
    ('PGTAP-CORSIA-COMUNE', 'PGTAP-CORSIA-Y', 'zeroerp_owner', now() - interval '1 hour',  now() - interval '1 hour',  true,  false, 'y verde', gen_random_uuid());

SELECT results_eq(
    $$SELECT processo_codice FROM maintenance.vw_job_run_da_guardare
       WHERE jobname = 'PGTAP-CORSIA-COMUNE'$$,
    $$VALUES ('PGTAP-CORSIA-X'::text)$$,
    'vw_job_run_da_guardare: il verde di Y non nasconde il rosso di X, che ha una corsia sua'
);

SELECT is(
    (SELECT ultimo_rosso_job_run_id FROM maintenance.vw_job_run_da_guardare
      WHERE jobname = 'PGTAP-CORSIA-COMUNE' AND processo_codice = 'PGTAP-CORSIA-X'),
    (SELECT id FROM maintenance.job_run_log
      WHERE jobname = 'PGTAP-CORSIA-COMUNE' AND processo_codice = 'PGTAP-CORSIA-X'),
    'vw_job_run_da_guardare: l''ultimo rosso di X e'' il suo, non quello piu'' recente di Y'
);

SELECT is(
    (SELECT falliti_ultimi_7_giorni FROM maintenance.vw_job_run_da_guardare
      WHERE jobname = 'PGTAP-CORSIA-COMUNE' AND processo_codice = 'PGTAP-CORSIA-X'),
    1::bigint,
    'vw_job_run_da_guardare: i falliti di X non contano il rosso di Y'
);

SELECT results_eq(
    $$SELECT processo_codice FROM maintenance.vw_job_run_corsie
       WHERE jobname = 'PGTAP-CORSIA-COMUNE' ORDER BY processo_codice$$,
    $$VALUES ('PGTAP-CORSIA-X'::text), ('PGTAP-CORSIA-Y'::text)$$,
    'vw_job_run_corsie: un nome usato da due processi sono due corsie'
);

SELECT * FROM finish();

ROLLBACK;
