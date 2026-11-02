-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- I job notturni strutturali girano anche dove pgAgent non c'e': ogni job
-- pgAgent dichiara nel catalogo dbops.processi o la sua posizione nella
-- convergenza di CI (e la procedura), o perche' ne resta fuori.
-- Brief: brief-db-job-notturni-in-ci, D3
--
-- Elenco test (plan 8):
--  1-3) le tre colonne esistono
--  4)   chk_processi_convergenza_ci c'e' ed e' convalidato
--  5)   ⭐ nessun job pgAgent senza posizione ne' esclusione («dimenticato»)
--  6)   ogni ci_procedura esiste
--  7)   ogni processo in elenco ha girato su QUESTO database: una riga ok in
--       maintenance.job_run_log che non sia un salto
--  8)   l'ordine rispetta le dipendenze note
--
-- Scopo:
--  - l'elenco sta nel catalogo; questo test lo legge, non ne tiene una copia;
--  - il 7 misura l'esito: in CI gira dopo ci_apply (90_end/ci_apply/20260926-10),
--    su dev dopo i giri di pgAgent.
-- ⚠️ Il 5 ripete il CHECK: serve dove il vincolo fosse ancora NOT VALID, e
--   dice QUALI righe, cosa che una convalida fallita non fa.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

SELECT has_column('dbops', 'processi', 'ci_ordine',     '1) dbops.processi.ci_ordine');
SELECT has_column('dbops', 'processi', 'ci_procedura',  '2) dbops.processi.ci_procedura');
SELECT has_column('dbops', 'processi', 'ci_esclusione', '3) dbops.processi.ci_esclusione');

SELECT is(
    (SELECT k.convalidated
       FROM pg_constraint k
      WHERE k.conrelid = 'dbops.processi'::regclass
        AND k.conname  = 'chk_processi_convergenza_ci'),
    true,
    '4) chk_processi_convergenza_ci esiste ed e'' convalidato'
);

SELECT is(
    (SELECT COALESCE(array_agg(p.codice ORDER BY p.codice), ARRAY[]::text[])
       FROM dbops.processi p
      WHERE p.jobname_pgagent IS NOT NULL
        AND p.ci_ordine IS NULL
        AND p.ci_esclusione IS NULL),
    ARRAY[]::text[],
    '5) ogni job pgAgent dichiara la posizione nella convergenza di CI o l''esclusione'
);

SELECT is(
    (SELECT COALESCE(array_agg(p.codice||' -> '||p.ci_procedura ORDER BY p.codice), ARRAY[]::text[])
       FROM dbops.processi p
      WHERE p.ci_procedura IS NOT NULL
        AND to_regprocedure(p.ci_procedura) IS NULL),
    ARRAY[]::text[],
    '6) ogni ci_procedura esiste'
);

SELECT is(
    (SELECT COALESCE(array_agg(p.codice ORDER BY p.codice), ARRAY[]::text[])
       FROM dbops.processi p
      WHERE p.ci_ordine IS NOT NULL
        AND p.attivo
        AND NOT EXISTS (
              SELECT 1
                FROM maintenance.job_run_log l
               WHERE l.jobname = p.codice
                 AND l.ok
                 AND l.message IS DISTINCT FROM 'skip: another run in progress')),
    ARRAY[]::text[],
    '7) ogni job strutturale in elenco ha girato su questo database (riga ok, non un salto)'
);

-- Le dipendenze che l'ordine deve rispettare, dette una per una:
--   la shadow prima del trigger di storico; l'insieme della storicizzazione
--   prima del DEFAULT che lo consuma; il lock di colonna dopo ATTIVO (ordine
--   di 90_end/ci_apply/20250627-31).
SELECT ok(
    (SELECT bool_and(a.ci_ordine < b.ci_ordine)
       FROM (VALUES ('automations_storico_provision', 'automations_storico'),
                    ('sync_storico_set_storicizza',   'apply_storicizza_weekly'),
                    ('automations_attivo',            'automations_lock_columns'))
            AS d(prima, dopo)
       JOIN dbops.processi a ON a.codice = d.prima
       JOIN dbops.processi b ON b.codice = d.dopo),
    '8) l''ordine rispetta le dipendenze: provision prima di storico, insieme prima del default, attivo prima del lock'
);

SELECT * FROM finish();
ROLLBACK;
