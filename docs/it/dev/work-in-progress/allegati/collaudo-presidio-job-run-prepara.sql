-- ------------------------------------------------------------
-- Collaudo del presidio dei job: ogni riga dice a chi tocca
-- Brief: brief-db-presidio-job-run-a-chi-tocca §5
--
-- PREPARA: mette nel giornale quattro corse di prova, una per causa, e controlla
-- nel database che ognuna abbia la causa e il destinatario attesi. Se un
-- controllo non torna, si ferma e NON lascia niente (transazione annullata).
--
-- Come si lancia (da chi possiede gli schemi, su dbdev):
--   set -a; . db/internal.env; set +a
--   psql -X -f docs/it/dev/work-in-progress/allegati/collaudo-presidio-job-run-prepara.sql
-- Poi il digest a mano, che non invia e non registra:
--   source backend/.venv/bin/activate
--   python backend/manage.py digest_presidi --cadenza giornaliera --secco
-- A collaudo finito:
--   psql -X -f docs/it/dev/work-in-progress/allegati/collaudo-presidio-job-run-pulisci.sql
--
-- Le corse attese nel digest, sotto `maintenance.vw_job_run_da_guardare`:
--   COLLAUDO-CAUSA-APPESA          → AMBIENTE       → chi gestisce il server
--   COLLAUDO-CAUSA-DISCO           → AMBIENTE       → chi gestisce il server
--   COLLAUDO-CAUSA-PROGRAMMA       → PROGRAMMA      → lo sviluppo
--   COLLAUDO-CAUSA-CONFIGURAZIONE  → CONFIGURAZIONE → l'amministratore
-- (Le righe vere del giornale, se ci sono, compaiono accanto: è giusto.)
--
-- ⚠️ Perché un processo e un codice di collaudo, e non smoke_notturno vero:
--   una corsa di prova su un processo vero cambierebbe il suo «ultimo segno di
--   vita» nel pannello dei processi. Il processo di collaudo è di canale CODA,
--   che il pannello dà come «su richiesta» e non guarda. Il codice di collaudo
--   serve perché oggi nessun codice vero dichiara CONFIGURAZIONE (§9.1).
-- ⚠️ Le righe restano finché non si lancia lo script di pulizia: il digest delle
--   7 di domani le vedrebbe.
-- ------------------------------------------------------------

\set ON_ERROR_STOP 1
-- ⚠️ Senza paginatore: con la tabella dentro `less` (END) la sessione aspetta, e
--   uscirne con Ctrl+C annulla la transazione prima del COMMIT.
\pset pager off

BEGIN;

-- Non si prepara due volte: righe rimaste da un collaudo precedente vanno tolte.
DO $gia$
BEGIN
    IF EXISTS (SELECT 1 FROM maintenance.job_run_log WHERE jobname LIKE 'COLLAUDO-CAUSA-%')
       OR EXISTS (SELECT 1 FROM dbops.processi WHERE codice = 'COLLAUDO-CAUSA' OR id = 9990) THEN
        RAISE EXCEPTION 'Ci sono gia'' righe di collaudo: lanciare prima collaudo-presidio-job-run-pulisci.sql';
    END IF;
END
$gia$;

-- Il processo di collaudo: canale CODA, i suoi fallimenti sono PROGRAMMA.
-- ⚠️ id esplicito (la tabella non ha identity): 9990, fuori dai valori del CSV.
INSERT INTO dbops.processi (id, codice, descrizione, classe, canale, causa_fallimento)
VALUES (9990, 'COLLAUDO-CAUSA', 'Processo di collaudo del presidio dei job (brief-db-presidio-job-run-a-chi-tocca §5). Da togliere col suo script di pulizia.',
        'MANUTENZIONE', 'CODA', 'PROGRAMMA');

-- Il codice di collaudo che dichiara CONFIGURAZIONE.
INSERT INTO config.codici_errore (codice, classe, note, causa_fallimento)
VALUES ('E_COLLAUDO_CAUSA_CONFIGURAZIONE', 'TECNICO',
        'Codice di collaudo del presidio dei job (brief-db-presidio-job-run-a-chi-tocca §5). Da togliere col suo script di pulizia.',
        'CONFIGURAZIONE');

-- 1) appesa da tre ore: il processo è morto senza chiudere la corsa.
INSERT INTO maintenance.job_run_log (jobname, stepname, processo_codice, origine, started_at)
VALUES ('COLLAUDO-CAUSA-APPESA', 'collaudo', 'COLLAUDO-CAUSA', 'PGAGENT', now() - interval '3 hours');

-- 2) disco pieno (SQLSTATE 53100).
INSERT INTO maintenance.job_run_log
    (jobname, stepname, processo_codice, origine, started_at, ended_at, ok, message, error_code, sqlstate)
VALUES ('COLLAUDO-CAUSA-DISCO', 'collaudo', 'COLLAUDO-CAUSA', 'PGAGENT',
        now() - interval '20 minutes', now() - interval '19 minutes', false,
        'collaudo: spazio su disco esaurito', '53100', '53100');

-- 3) un difetto del programma: codice non a registro, decide il processo.
INSERT INTO maintenance.job_run_log
    (jobname, stepname, processo_codice, origine, started_at, ended_at, ok, message, error_code)
VALUES ('COLLAUDO-CAUSA-PROGRAMMA', 'collaudo', 'COLLAUDO-CAUSA', 'COMMAND',
        now() - interval '20 minutes', now() - interval '19 minutes', false,
        'collaudo: regressioni negli smoke', 'SMOKE_REGRESSIONI');

-- 4) un'impostazione dell'applicazione: il codice dichiara CONFIGURAZIONE.
INSERT INTO maintenance.job_run_log
    (jobname, stepname, processo_codice, origine, started_at, ended_at, ok, message, error_code, sqlstate)
VALUES ('COLLAUDO-CAUSA-CONFIGURAZIONE', 'collaudo', 'COLLAUDO-CAUSA', 'PGAGENT',
        now() - interval '20 minutes', now() - interval '19 minutes', false,
        'collaudo: impostazione mancante', 'E_COLLAUDO_CAUSA_CONFIGURAZIONE', 'P0001');

-- Il controllo: causa e destinatario attesi, letti dal database.
DO $controllo$
DECLARE
    v_sbagliate text;
BEGIN
    SELECT string_agg(format('%s: atteso %s/%s, trovato %s/%s',
                             a.jobname, a.causa, a.chi, coalesce(v.causa, '-'), coalesce(pc.chi_agisce, '-')),
                      '; ' ORDER BY a.jobname)
      INTO v_sbagliate
      FROM (VALUES ('COLLAUDO-CAUSA-APPESA',         'AMBIENTE',       'SISTEMISTA'),
                   ('COLLAUDO-CAUSA-DISCO',          'AMBIENTE',       'SISTEMISTA'),
                   ('COLLAUDO-CAUSA-PROGRAMMA',      'PROGRAMMA',      'SVILUPPO'),
                   ('COLLAUDO-CAUSA-CONFIGURAZIONE', 'CONFIGURAZIONE', 'AMMINISTRATORE')) a(jobname, causa, chi)
      LEFT JOIN maintenance.vw_job_run_da_guardare v ON v.jobname = a.jobname
      LEFT JOIN dbops.presidi_cause pc
             ON pc.vista = 'maintenance.vw_job_run_da_guardare' AND pc.causa = v.causa
     WHERE v.causa IS DISTINCT FROM a.causa OR pc.chi_agisce IS DISTINCT FROM a.chi;

    IF v_sbagliate IS NOT NULL THEN
        RAISE EXCEPTION 'Collaudo NON superato nel database, niente e'' stato lasciato: %', v_sbagliate;
    END IF;
END
$controllo$;

-- Quello che il digest dovrà mostrare.
SELECT v.jobname, v.motivo, v.causa, pc.chi_agisce
  FROM maintenance.vw_job_run_da_guardare v
  JOIN dbops.presidi_cause pc
    ON pc.vista = 'maintenance.vw_job_run_da_guardare' AND pc.causa = v.causa
 WHERE v.jobname LIKE 'COLLAUDO-CAUSA-%'
 ORDER BY pc.chi_agisce, v.jobname;

COMMIT;
